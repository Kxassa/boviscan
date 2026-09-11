import { useEffect, useState } from "react";

/** Synthetic live feed when API is empty / offline. */
export function useMockLiveWeight(enabled = true) {
  const [kg, setKg] = useState(412);
  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      setKg((v) => Math.round((v + (Math.random() - 0.5) * 8) * 10) / 10);
    }, 1500);
    return () => clearInterval(id);
  }, [enabled]);
  return kg;
}
