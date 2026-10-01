import { useEffect, useRef, useState } from "react";
import { getChatStatus, sendChatMessage, getErrorMessage } from "../api/api";
import { formatPercent } from "../utils/format";
import Icon from "./Icon";

// The backend accepts at most 20 messages, alternating and starting with
// the user; an odd-length tail always starts with a user turn.
const MAX_HISTORY = 19;

const SUGGESTIONS = {
  xray: {
    withSubject: [
      "What does this result mean?",
      "What does the heatmap show?",
      "How reliable is this screening?",
      "What should happen next?",
    ],
    withoutSubject: [
      "How does this X-ray screening work?",
      "What is pneumonia?",
      "What can this tool not detect?",
    ],
    prompt: "Ask anything about this screening result:",
    empty: "No X-ray analyzed yet — you can still ask general questions.",
  },
  document: {
    withSubject: [
      "What do these results mean?",
      "Which values are high or low?",
      "What is a reference range?",
      "What should happen next?",
    ],
    withoutSubject: [
      "What can this report analyzer read?",
      "What is a reference range?",
      "What do High and Low mean?",
    ],
    prompt: "Ask anything about this lab report:",
    empty: "No report analyzed yet — you can still ask general questions.",
  },
};

function describeSubject(report, document) {
  if (report) {
    return `Discussing: ${report.prediction} result (pneumonia probability ${formatPercent(
      report.pneumonia_probability
    )}%)`;
  }

  const findings = document.findings || [];
  const flagged = findings.filter((f) => f.status === "High" || f.status === "Low").length;
  return `Discussing: ${document.file_name} (${findings.length} value${
    findings.length === 1 ? "" : "s"
  } read, ${flagged} outside range)`;
}

/**
 * Floating AI assistant. mode "xray" takes the analyzed `report`, mode
 * "document" the analyzed lab `document`; the backend answers from that
 * result's data only.
 */
export default function AiAssistant({ mode = "xray", report = null, document = null }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);

  const subjectKey = report ? `report-${report.id}` : document ? `document-${document.id}` : "none";
  const hasSubject = Boolean(report || document);
  const text = SUGGESTIONS[mode];

  useEffect(() => {
    setMessages([]);
    setError("");
  }, [subjectKey]);

  useEffect(() => {
    if (!open || status) return;

    getChatStatus()
      .then(setStatus)
      .catch((statusRequestError) =>
        setStatusError(getErrorMessage(statusRequestError, "Unable to reach the chatbot service."))
      );
  }, [open, status]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, sending]);

  async function send(text) {
    const question = text.trim();
    if (!question || sending) return;

    const history = [...messages, { role: "user", content: question }];

    setMessages(history);
    setInput("");
    setError("");
    setSending(true);

    try {
      // Only role/content go to the backend; `source` is display-only.
      const payload = history
        .slice(-MAX_HISTORY)
        .map(({ role, content }) => ({ role, content }));
      const data = await sendChatMessage(
        { reportId: report?.id, documentId: document?.id },
        payload
      );
      setMessages([
        ...history,
        { role: "assistant", content: data.reply, source: data.source, model: data.model },
      ]);
    } catch (requestError) {
      // Roll the unanswered question back into the input so the
      // conversation keeps alternating user/assistant for the next send.
      setMessages(messages);
      setInput(question);
      setError(getErrorMessage(requestError, "The chatbot request failed. Please try again."));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(input);
    }
  }

  const offlineMode = status && !status.llm_available;
  const suggestions = hasSubject ? text.withSubject : text.withoutSubject;

  return (
    <>
      {open && (
        <section className="chatbot-panel" aria-label="MediVision AI assistant">
          <header className="chatbot-header">
            <span className="chatbot-avatar">
              <Icon name="sparkles" size={18} />
            </span>
            <div className="chatbot-header-text">
              <strong>MediVision Assistant</strong>
              <span>AI explanations · not a diagnosis</span>
            </div>
            <button
              type="button"
              className="chatbot-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              <Icon name="x" size={20} />
            </button>
          </header>

          <div className="chatbot-context">
            {hasSubject ? describeSubject(report, document) : text.empty}
          </div>

          <div className="chatbot-messages" ref={listRef} aria-live="polite">
            {statusError && <div className="chatbot-error">{statusError}</div>}

            {offlineMode && (
              <div className="chatbot-note">
                Offline mode: no AI model is connected right now, so common questions get
                built-in answers.
              </div>
            )}

            {messages.length === 0 && !statusError && (
              <div className="chatbot-suggestions">
                <p>{text.prompt}</p>
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => send(suggestion)}
                    disabled={!status || sending}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {messages.map((message, index) => (
              <div key={index} className={`chatbot-message chatbot-${message.role}`}>
                {message.content}
                {message.source && (
                  <span className="chatbot-source">
                    {message.source === "nvidia"
                      ? `AI model · ${message.model}`
                      : message.source === "local_llm"
                        ? `Local AI model · ${message.model}`
                        : "Built-in answer"}
                  </span>
                )}
              </div>
            ))}

            {sending && (
              <div className="chatbot-message chatbot-assistant chatbot-typing">Thinking…</div>
            )}

            {error && <div className="chatbot-error">{error}</div>}
          </div>

          <form
            className="chatbot-input"
            onSubmit={(event) => {
              event.preventDefault();
              send(input);
            }}
          >
            <textarea
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your question…"
              maxLength={4000}
              disabled={!status}
              aria-label="Your question"
            />
            <button
              type="submit"
              className="primary-button"
              disabled={!status || sending || !input.trim()}
            >
              <Icon name="arrowRight" size={18} />
              <span>Send</span>
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className="chatbot-launcher"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close AI assistant" : "Open AI assistant"}
        aria-expanded={open}
      >
        <Icon name={open ? "x" : "chat"} size={22} />
        {!open && <span>Ask AI</span>}
      </button>
    </>
  );
}
