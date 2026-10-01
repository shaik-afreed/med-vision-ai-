import { useEffect, useRef, useState } from "react";
import { getChatStatus, sendChatMessage, getErrorMessage } from "../api/api";
import { formatPercent } from "../utils/format";
import Icon from "./Icon";

// The backend accepts at most 20 messages, alternating and starting with
// the user; an odd-length tail always starts with a user turn.
const MAX_HISTORY = 19;

const SUGGESTIONS_WITH_RESULT = [
  "What does this result mean?",
  "What does the heatmap show?",
  "How reliable is this screening?",
  "What should happen next?",
];

const SUGGESTIONS_WITHOUT_RESULT = [
  "How does this X-ray screening work?",
  "What is pneumonia?",
  "What can this tool not detect?",
];

export default function XRayChatbot({ report }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);

  const reportId = report?.id ?? null;

  useEffect(() => {
    setMessages([]);
    setError("");
  }, [reportId]);

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
      const data = await sendChatMessage(reportId, payload);
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
  const suggestions = report ? SUGGESTIONS_WITH_RESULT : SUGGESTIONS_WITHOUT_RESULT;

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
            {report
              ? `Discussing: ${report.prediction} result (pneumonia probability ${formatPercent(
                  report.pneumonia_probability
                )}%)`
              : "No X-ray analyzed yet — you can still ask general questions."}
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
                <p>Ask anything about this screening result:</p>
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
