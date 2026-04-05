export const ROLE_OPTIONS = [
  {
    value: "platform_admin",
    label: "Platform admin",
    shortLabel: "Platform",
    description: "Manage NGOs, verify people, and oversee the shared registry.",
  },
  {
    value: "ngo_admin",
    label: "NGO admin",
    shortLabel: "NGO",
    description: "Enroll verified people, manage eligibility, and issue passes.",
  },
  {
    value: "aid_worker",
    label: "Aid worker",
    shortLabel: "Aid worker",
    description: "Verify passes at the gate and record delivery outcomes.",
  },
];

export function getRoleMeta(role) {
  return ROLE_OPTIONS.find((option) => option.value === role) || null;
}

export function getRoleLabel(role) {
  return getRoleMeta(role)?.label || role?.replaceAll("_", " ") || "Unknown role";
}
