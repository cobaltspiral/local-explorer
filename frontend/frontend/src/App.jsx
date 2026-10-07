import { useEffect, useState } from "react";
import Mochi from "./Mochi.jsx";
import { useTypewriter } from "./useTypewriter";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// "value" must match exactly what the backend accepts.
const MOODS = [
  { label: "Cosy", value: "cosy" },
  { label: "Outdoors", value: "outdoors" },
  { label: "Adventurous", value: "adventurous" },
  { label: "Creative", value: "creative" },
  { label: "Social", value: "social" },
  { label: "Food", value: "food" },
  { label: "History", value: "history" },
  { label: "Thrifting", value: "thrifting" },
  { label: "Unusual", value: "unusual" },
  { label: "Surprise me", value: "surprise" },
];
const DURATIONS = [
  { label: "30 min", value: "30min" },
  { label: "1-2 hrs", value: "1-2hrs" },
  { label: "Half day", value: "half_day" },
  { label: "Full day", value: "full_day" },
  { label: "Multiple days", value: "multiple_days" },
];
const TIMES = [
  { label: "Morning", value: "morning" },
  { label: "Afternoon", value: "afternoon" },
  { label: "Evening", value: "evening" },
  { label: "Night", value: "night" },
  { label: "Anytime", value: "anytime" },
];

const QUESTIONS = [
  { key: "location", text: "Hi, I'm Mochi! Which city or town shall we explore today?" },
  { key: "mood", text: "Nice! What are you in the mood for?", options: MOODS },
  { key: "duration", text: "How much time do you have?", options: DURATIONS },
  { key: "time_of_day", text: "And what time of day are you heading out?", options: TIMES },
];

const LOADING_MSGS = [
  "Sniffing out spots...",
  "Checking the map...",
  "Thinking hard... this can take a minute!",
  "Almost there. Find your shoes!",
];

function LocationInput({ onSubmit }) {
  const [value, setValue] = useState("");
  return (
    <form
      className="choices"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim().length >= 2) onSubmit(value.trim());
      }}
    >
      <input
        className="nes-input"
        autoFocus
        placeholder="e.g. Edinburgh"
        value={value}
        maxLength={100}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="nes-btn is-primary">
        Go!
      </button>
    </form>
  );
}

function Options({ options, onPick }) {
  return (
    <div className="choices grid">
      {options.map((o) => (
        <button key={o.value} className="nes-btn" onClick={() => onPick(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({
    location: "",
    mood: "",
    duration: "",
    time_of_day: "",
  });
  const [phase, setPhase] = useState("asking"); // asking | loading | result | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [loadIdx, setLoadIdx] = useState(0);
  const [mouthOpen, setMouthOpen] = useState(false);

  // What is Mochi saying right now?
  let speech = "";
  if (phase === "asking") speech = QUESTIONS[step].text;
  else if (phase === "loading") speech = LOADING_MSGS[loadIdx];
  else if (phase === "result") speech = result.intro;
  else speech = errorMsg;

  const { shown, done } = useTypewriter(speech);

  // Rotate the loading messages
  useEffect(() => {
    if (phase !== "loading") return;
    setLoadIdx(0);
    const id = setInterval(
      () => setLoadIdx((i) => Math.min(i + 1, LOADING_MSGS.length - 1)),
      6000
    );
    return () => clearInterval(id);
  }, [phase]);

  // Flap Pip's mouth while the text is typing
  useEffect(() => {
    if (done) {
      setMouthOpen(false);
      return;
    }
    const id = setInterval(() => setMouthOpen((m) => !m), 140);
    return () => clearInterval(id);
  }, [done]);

  const frame = !done
    ? mouthOpen ? "talking" : "idle"
    : phase === "result" ? "happy" : "idle";

  async function getRecommendation(finalAnswers) {
    setPhase("loading");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 180000); // 3 minutes
    try {
      const res = await fetch(`${API_URL}/api/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalAnswers),
        signal: controller.signal,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Something went wrong. Try again!"
        );
      }
      setResult(data);
      setPhase("result");
    } catch (err) {
      if (err.name === "AbortError") {
        setErrorMsg("That took too long. Shall we try again?");
      } else if (err instanceof TypeError) {
        setErrorMsg("I can't reach my brain! Is the backend running?");
      } else {
        setErrorMsg(err.message);
      }
      setPhase("error");
    } finally {
      clearTimeout(timer);
    }
  }

  function choose(value) {
    const key = QUESTIONS[step].key;
    const next = { ...answers, [key]: value };
    setAnswers(next);
    if (step < QUESTIONS.length - 1) setStep(step + 1);
    else getRecommendation(next);
  }

  function startOver() {
    setStep(0);
    setAnswers({ location: "", mood: "", duration: "", time_of_day: "" });
    setResult(null);
    setErrorMsg("");
    setPhase("asking");
  }

  return (
    <main className="app">
      <h1 className="title">Touch Grass</h1>

      <section className="stage">
        <Mochi frame={frame} bounce={phase === "loading"} />
        <div className="nes-balloon from-left bubble">
          <p>{shown}</p>
        </div>
      </section>

      {phase === "asking" && done &&
        (step === 0 ? (
          <LocationInput onSubmit={choose} />
        ) : (
          <Options options={QUESTIONS[step].options} onPick={choose} />
        ))}

      {phase === "error" && done && (
        <div className="choices">
          <button className="nes-btn is-primary" onClick={() => getRecommendation(answers)}>
            Try again
          </button>
          <button className="nes-btn" onClick={startOver}>
            Start over
          </button>
        </div>
      )}

      {phase === "result" && done && (
        <section className="result">
          {answers.mood === "surprise" && (
            <p className="note">I picked "{result.mood_used}" for you!</p>
          )}
          {result.stops.map((s, i) => (
            <div key={s.name} className="nes-container is-rounded stop">
              <p className="stop-name">
                {i + 1}. {s.name}
              </p>
              <p className="meta">
                {s.category} · {s.distance_m} m away
              </p>
              {s.why && <p>{s.why}</p>}
              {s.tip && <p className="tip">Tip: {s.tip}</p>}
            </div>
          ))}
          <div className="choices">
            <button className="nes-btn is-primary" onClick={startOver}>
              Ask me again
            </button>
          </div>
        </section>
      )}
    </main>
  );
}