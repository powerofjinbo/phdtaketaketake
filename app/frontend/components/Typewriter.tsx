"use client";

import { useEffect, useState } from "react";

/** Types, pauses, and erases each word in turn. Static under reduced motion. */
export default function Typewriter({
  words,
  className = "",
}: {
  words: string[];
  className?: string;
}) {
  const [i, setI] = useState(0);
  const [text, setText] = useState(words[0]);
  const [deleting, setDeleting] = useState(false);
  const [still, setStill] = useState(false);

  useEffect(() => {
    const t = setTimeout(
      () => setStill(window.matchMedia("(prefers-reduced-motion: reduce)").matches),
      0
    );
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (still) return;
    const word = words[i % words.length];
    let delay = deleting ? 38 : 70;
    if (!deleting && text === word) delay = 2200;
    if (deleting && text === "") delay = 300;
    const t = setTimeout(() => {
      if (!deleting && text === word) setDeleting(true);
      else if (deleting && text === "") {
        setDeleting(false);
        setI((n) => n + 1);
      } else {
        setText(deleting ? word.slice(0, text.length - 1) : word.slice(0, text.length + 1));
      }
    }, delay);
    return () => clearTimeout(t);
  }, [text, deleting, i, words, still]);

  return (
    <span className={className}>
      {text}
      {!still && <span className="caret" aria-hidden="true" />}
    </span>
  );
}
