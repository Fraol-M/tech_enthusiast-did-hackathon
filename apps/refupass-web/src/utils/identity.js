export function formatSubjectId(subject, { head = 8, tail = 6 } = {}) {
  if (!subject) {
    return "Not linked";
  }
  if (subject.length <= head + tail + 3) {
    return subject;
  }
  return `${subject.slice(0, head)}...${subject.slice(-tail)}`;
}

export function describeIdentity(person) {
  if (!person?.authSubject) {
    return "Identity not linked";
  }
  if (person.identityStatus === "verified_digital") {
    return "Verified with eSignet";
  }
  if (person.identityStatus?.startsWith("verified")) {
    return "Verified identity";
  }
  return "Registry record";
}
