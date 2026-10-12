export const fondo = (a: string, b: string): React.CSSProperties => ({
  background: `linear-gradient(135deg, ${a}, ${b})`,
  justifyContent: "center",
  alignItems: "center",
  fontFamily: "Helvetica, Arial, sans-serif",
  color: "white",
  padding: 120,
});
