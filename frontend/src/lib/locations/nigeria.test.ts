import { describe, expect, it } from "vitest";
import { NIGERIA_LGAS, NIGERIA_STATES, matchLga, matchState } from "./nigeria";

// Official number of LGAs per state (774 in total).
const OFFICIAL: Record<string, number> = {
  Abia: 17, Adamawa: 21, "Akwa Ibom": 31, Anambra: 21, Bauchi: 20, Bayelsa: 8, Benue: 23, Borno: 27, "Cross River": 18,
  Delta: 25, Ebonyi: 13, Edo: 18, Ekiti: 16, Enugu: 17, FCT: 6, Gombe: 11, Imo: 27, Jigawa: 27, Kaduna: 23, Kano: 44,
  Katsina: 34, Kebbi: 21, Kogi: 21, Kwara: 16, Lagos: 20, Nasarawa: 13, Niger: 25, Ogun: 20, Ondo: 18, Osun: 30, Oyo: 33,
  Plateau: 17, Rivers: 23, Sokoto: 23, Taraba: 16, Yobe: 17, Zamfara: 14,
};

describe("Nigeria states and LGAs", () => {
  it("has all 36 states + FCT and all 774 LGAs, with no duplicates in a state", () => {
    expect(NIGERIA_STATES).toHaveLength(37);
    for (const [state, count] of Object.entries(OFFICIAL)) {
      expect(NIGERIA_LGAS[state], state).toHaveLength(count);
      expect(new Set(NIGERIA_LGAS[state]).size, state).toBe(count);
    }
    expect(Object.values(NIGERIA_LGAS).reduce((n, l) => n + l.length, 0)).toBe(774);
  });

  it("matches states however the map writes them", () => {
    expect(matchState("Lagos State")).toBe("Lagos");
    expect(matchState("Federal Capital Territory")).toBe("FCT");
    expect(matchState("Abuja")).toBe("FCT");
    expect(matchState("akwa-ibom")).toBe("Akwa Ibom");
    expect(matchState("Nassarawa")).toBe("Nasarawa");
    expect(matchState("Greater Accra")).toBeUndefined();
  });

  it("matches LGAs within their own state only", () => {
    expect(matchLga("Lagos", "eti osa")).toBe("Eti-Osa");
    expect(matchLga("Lagos", "Somolu")).toBe("Shomolu");
    expect(matchLga("FCT", "AMAC")).toBe("Municipal Area Council (AMAC)");
    expect(matchLga("Ogun", "Egbado North")).toBe("Yewa North");
    expect(matchLga("Adamawa", "Girei")).toBe("Girei");
    expect(matchLga("Adamawa", "Grie")).toBe("Girei"); // older misspelling still recognised
    expect(NIGERIA_LGAS.Adamawa).toEqual(expect.arrayContaining(["Fufore", "Girei", "Guyuk"]));
    expect(matchLga("Kano", "Eti-Osa")).toBeUndefined();
    expect(matchLga("Lagos", "Surulere")).toBe("Surulere");
    expect(matchLga("Oyo", "Surulere")).toBe("Surulere"); // both states have a Surulere
  });
});
