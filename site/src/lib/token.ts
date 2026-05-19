import { v4 as uuidv4 } from "uuid";

export function generateToken(): string {
  return uuidv4().replace(/-/g, "") + uuidv4().replace(/-/g, "");
}

export function generateDeviceId(): string {
  return "pc_" + uuidv4().replace(/-/g, "").slice(0, 16);
}

export function generateMobileId(): string {
  return "mob_" + uuidv4().replace(/-/g, "").slice(0, 16);
}
