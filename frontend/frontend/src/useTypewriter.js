import { useEffect, useState } from "react";

export function useTypewriter(text, speed = 25) {
  const [state, setState] = useState({ text: "", count: 0 });
  const count = state.text === text ? state.count : 0;

  useEffect(() => {
    if (!text) return;
    setState({ text, count: 0 });
    const id = setInterval(() => {
      setState((s) => {
        if (s.text !== text) return s;
        if (s.count >= text.length) {
          clearInterval(id);
          return s;
        }
        return { text, count: s.count + 1 };
      });
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return { shown: text.slice(0, count), done: count >= text.length };
}