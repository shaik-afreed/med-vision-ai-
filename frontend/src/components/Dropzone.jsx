import { useState } from "react";
import Icon from "./Icon";

/**
 * Click-or-drop file picker. The real <input type="file"> stays in the DOM
 * (visually hidden, still keyboard-focusable) so it works with screen
 * readers, keyboards and automated tests; the label around it is the
 * clickable/droppable surface.
 */
export default function Dropzone({
  accept,
  file,
  previewUrl,
  onFile,
  icon = "upload",
  title,
  changeTitle,
  hint,
}) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);

    const dropped = event.dataTransfer.files?.[0];
    if (dropped) onFile(dropped);
  }

  return (
    <label
      className={`dropzone ${dragging ? "drag-over" : ""} ${file ? "has-file" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        className="sr-only"
        accept={accept}
        onChange={(event) => {
          onFile(event.target.files?.[0] ?? null);
          // Allow choosing the same file again after a rejection or reset.
          event.target.value = "";
        }}
      />

      {previewUrl ? (
        <img className="dropzone-preview" src={previewUrl} alt="Preview of the selected X-ray" />
      ) : (
        <span className="dropzone-icon">
          <Icon name={icon} size={26} />
        </span>
      )}

      <span className="dropzone-title">{file ? changeTitle : title}</span>
      <span className="dropzone-hint">{hint}</span>
    </label>
  );
}
