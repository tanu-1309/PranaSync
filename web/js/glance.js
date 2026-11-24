// "At a glance" on Home: the three risk areas as classes (never a percentage), the parameters behind each, how much evidence each rests on, and what is missing.
// The classes come from the trained model on the server; no language model writes anything here.
import { glanceRisk } from "./risk.js";

export function glance() {
  return glanceRisk();
}
