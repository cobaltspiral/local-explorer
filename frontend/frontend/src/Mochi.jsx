const PALETTE = {
  k: "#2d2a32", // outline, eyes, mouth
  g: "#7bd36b", // body
  l: "#b9f27c", // leaf
  p: "#ff9eb5", // cheeks
};

// 16 columns x 16 rows. "." means transparent.
const BASE = [
  "................",
  ".......kk.......",
  "......kllk......",
  ".....kllkkk.....",
  ".......kk.......",
  "...kkkkkkkkkk...",
  "..kggggggggggk..",
  "..kggkkggkkggk..",
  "..kggkkggkkggk..",
  "..kppggggggppk..",
  "..kggggkkggggk..", // mouth row 1
  "..kggggggggggk..", // mouth row 2
  "...kkkkkkkkkk...",
  "....kk......kk..",
  "................",
  "................",
];

function withRows(base, overrides) {
  return base.map((row, i) => overrides[i] ?? row);
}

const FRAMES = {
  idle: BASE,
  talking: withRows(BASE, {
    10: "..kgggkkkkgggk..",
    11: "..kgggkkkkgggk..",
  }),
  happy: withRows(BASE, {
    8: "..kggggggggggk..",
    10: "..kgggkggkgggk..",
    11: "..kggggkkggggk..",
  }),
};

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