import { useEffect, useState } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function SearchBar({ value, onChange }: Props) {
  const [text, setText] = useState(value);

  useEffect(() => {
    setText(value);
  }, [value]);

  useEffect(() => {
    if (text === value) return;
    const t = setTimeout(() => onChange(text), 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  return (
    <input
      className="search"
      type="search"
      placeholder="Search by title, company or skill..."
      value={text}
      onChange={(e) => setText(e.target.value)}
    />
  );
}
