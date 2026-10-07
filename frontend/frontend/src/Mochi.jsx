export default function Mochi({ frame = "idle", bounce = false, size = 128 }) {
  return (
    <img
      src={`/mochi-${frame}.png`}
      width={size}
      height={size}
      className={bounce ? "mochi bounce" : "mochi"}
      alt="Mochi, the pixel guide"
    />
  );
}