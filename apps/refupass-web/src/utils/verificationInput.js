import jsQR from "jsqr";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";

GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

const PDF_FIELD_MAPPINGS = [
  ["Beneficiary ID", "subjectId"],
  ["Household ID", "householdId"],
  ["Full Name", "fullName"],
  ["Program", "programName"],
  ["Aid Cycle", "aidCycle"],
  ["Distribution Site", "distributionSite"],
  ["Family Size", "familySize"],
  ["Ration Tier", "rationTier"],
  ["Entitlement Status", "entitlementStatus"],
  ["Valid From", "validFrom"],
  ["Valid Until", "validUntil"],
];

function extractPdfMetadata(lines) {
  const metadata = {};

  for (const [label, key] of PDF_FIELD_MAPPINGS) {
    const index = lines.findIndex((line) => line === label);
    if (index === -1 || index + 1 >= lines.length) {
      continue;
    }
    const value = lines[index + 1]?.trim();
    if (!value) {
      continue;
    }
    metadata[key] = key === "familySize" ? Number.parseInt(value, 10) || 0 : value;
  }

  return metadata;
}

async function renderAndDecodeQr(page) {
  const scales = [2, 3, 4];

  for (const scale of scales) {
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
      continue;
    }

    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);

    await page.render({
      canvasContext: context,
      viewport,
    }).promise;

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const decoded = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: "attemptBoth",
    });

    if (decoded?.data) {
      return decoded.data;
    }
  }

  return null;
}

async function extractPdfVerificationInput(file) {
  const pdf = await getDocument({
    data: new Uint8Array(await file.arrayBuffer()),
  }).promise;

  const textLines = [];
  let credentialText = "";

  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const textContent = await page.getTextContent();
    textLines.push(
      ...textContent.items
        .map((item) => ("str" in item ? item.str : ""))
        .map((line) => line.trim())
        .filter(Boolean),
    );

    if (!credentialText) {
      credentialText = (await renderAndDecodeQr(page)) || "";
    }
  }

  if (!credentialText) {
    throw new Error("Could not find a verification QR inside this PDF.");
  }

  return {
    credentialText,
    credentialMetadata: extractPdfMetadata(textLines),
    sourceLabel: `Loaded QR from ${file.name}`,
  };
}

async function decodeQrFromImageFile(file) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error("Could not read this QR image."));
      element.src = objectUrl;
    });

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
      throw new Error("Could not prepare image verification.");
    }

    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const decoded = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: "attemptBoth",
    });

    if (!decoded?.data) {
      throw new Error("Could not find a verification QR inside this image.");
    }

    return {
      credentialText: decoded.data,
      credentialMetadata: null,
      sourceLabel: `Loaded QR from ${file.name}`,
    };
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function extractVerificationInput(file) {
  if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
    return extractPdfVerificationInput(file);
  }

  if (file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp)$/i.test(file.name)) {
    return decodeQrFromImageFile(file);
  }

  throw new Error("Upload a RefuProof PDF or a mobile pass image.");
}
