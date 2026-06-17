import { useState, type KeyboardEvent } from "react";
import styles from "./KeywordInput.module.css";

interface KeywordInputProps {
  value: string[];
  onChange: (newValue: string[]) => void;
  placeholder?: string;
}

export default function KeywordInput({ value, onChange, placeholder = "Type and press Enter..." }: KeywordInputProps) {
  const [inputValue, setInputValue] = useState("");

  const addTag = () => {
    const trimmed = inputValue.trim().toLowerCase();
    if (trimmed && !value.includes(trimmed)) {
      const updated = [...value, trimmed];
      onChange(updated);
      setInputValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Backspace" && !inputValue && value.length > 0) {
      // Remove last tag if input is empty and user hits backspace
      const updated = value.slice(0, -1);
      onChange(updated);
    }
  };

  const removeTag = (indexToRemove: number) => {
    const updated = value.filter((_, index) => index !== indexToRemove);
    onChange(updated);
  };

  return (
    <div className={styles.container}>
      {value.map((tag, index) => (
        <span key={`${tag}-${index}`} className={styles.tag}>
          {tag}
          <button
            type="button"
            className={styles.removeBtn}
            onClick={() => removeTag(index)}
          >
            &times;
          </button>
        </span>
      ))}
      <input
        className={styles.input}
        type="text"
        placeholder={value.length === 0 ? placeholder : ""}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={addTag}
      />
    </div>
  );
}
