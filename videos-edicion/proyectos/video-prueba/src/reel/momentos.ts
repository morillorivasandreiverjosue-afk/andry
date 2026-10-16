// Tiempos (en segundos) sacados del video original

// Cambios de escena: flash + whoosh + zoom
export const CORTES = [5, 12, 17, 22, 29, 34, 41, 46, 53, 60, 67];

// Golpes fuertes: zoom de impacto + sacudida
export const GOLPES = [1.0, 8.0, 17.2, 43.0, 49.0, 55.0, 67.2];

// La voz se corta a 66,9 s; desde aquí se ve la llamada final a seguir la cuenta
export const INICIO_CTA = 69;

export type Efecto = { seg: number; sonido: string; volumen: number };

export const EFECTOS: Efecto[] = [
  { seg: 0.0, sonido: "whoosh", volumen: 0.7 },
  { seg: 1.0, sonido: "boom", volumen: 0.9 },
  { seg: 7.9, sonido: "error", volumen: 0.45 },
  { seg: 12.3, sonido: "pop", volumen: 0.6 },
  { seg: 13.0, sonido: "pop", volumen: 0.6 },
  { seg: 13.6, sonido: "pop", volumen: 0.6 },
  { seg: 14.2, sonido: "error", volumen: 0.4 },
  { seg: 17.2, sonido: "boom", volumen: 0.85 },
  { seg: 22.3, sonido: "tick", volumen: 0.5 },
  { seg: 22.6, sonido: "tick", volumen: 0.5 },
  { seg: 23.0, sonido: "tick", volumen: 0.5 },
  { seg: 23.3, sonido: "tick", volumen: 0.5 },
  { seg: 29.2, sonido: "tick", volumen: 0.4 },
  { seg: 29.5, sonido: "tick", volumen: 0.4 },
  { seg: 29.8, sonido: "tick", volumen: 0.4 },
  { seg: 30.1, sonido: "tick", volumen: 0.4 },
  { seg: 30.4, sonido: "tick", volumen: 0.4 },
  { seg: 30.7, sonido: "tick", volumen: 0.4 },
  { seg: 31.0, sonido: "ding", volumen: 0.5 },
  { seg: 35.0, sonido: "pop", volumen: 0.6 },
  { seg: 36.0, sonido: "pop", volumen: 0.6 },
  { seg: 36.6, sonido: "pop", volumen: 0.6 },
  { seg: 37.1, sonido: "pop", volumen: 0.6 },
  { seg: 41.5, sonido: "riser", volumen: 0.5 },
  { seg: 43.0, sonido: "boom", volumen: 0.9 },
  { seg: 47.0, sonido: "pop", volumen: 0.6 },
  { seg: 48.0, sonido: "pop", volumen: 0.6 },
  { seg: 48.2, sonido: "pop", volumen: 0.6 },
  { seg: 49.0, sonido: "error", volumen: 0.45 },
  { seg: 50.1, sonido: "ding", volumen: 0.5 },
  { seg: 55.0, sonido: "boom", volumen: 0.85 },
  { seg: 61.0, sonido: "pop", volumen: 0.6 },
  { seg: 62.0, sonido: "pop", volumen: 0.6 },
  { seg: 63.0, sonido: "pop", volumen: 0.6 },
  { seg: 65.2, sonido: "riser", volumen: 0.5 },
  { seg: 67.2, sonido: "boom", volumen: 0.9 },
  { seg: 68.1, sonido: "ding", volumen: 0.5 },
  { seg: 69.0, sonido: "whoosh", volumen: 0.6 },
];
