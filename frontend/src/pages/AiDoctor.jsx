import { useEffect, useRef, useState } from "react";
import { getChatStatus, sendHealthMessage, getErrorMessage } from "../api/api";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";

// The backend accepts at most 20 messages, alternating and starting with the
// user; an odd-length tail always starts with a user turn.
const MAX_HISTORY = 19;

const STARTERS = [
  { label: "Headache", text: "I have a headache. What can I do?" },
  { label: "Cold and cough", text: "I have a cold and cough for 3 days. What should I do?" },
  { label: "Fever", text: "I have a fever. What should I do and when should I see a doctor?" },
  { label: "Stomach upset", text: "I have stomach pain and loose motions." },
  { label: "Body pain", text: "I have body aches and feel tired." },
  { label: "Sleep and stress", text: "I can't sleep and I feel stressed." },
];

const WELCOME =
  "Hello, I'm your AI Doctor. Tell me what is bothering you, who it is for (age), and how long " +
  "it has lasted, and I'll explain what it commonly is, what you can do at home, and when to see " +
  "a real doctor.";

/**
 * AI Doctor: a full-page chat for everyday health questions. General health
 * information only; the backend answers emergencies with a fixed urgent-care
 * message and never sends any patient record.
 */
export default function AiDoctor() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    getChatStatus()
      .then(setStatus)
      .catch(() => setStatus({ llm_available: false }));
  }, []);

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
      const payload = history.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content }));
      const data = await sendHealthMessage(payload);
      setMessages([
        ...history,
        { role: "assistant", content: data.reply, source: data.source, model: data.model },
      ]);
    } catch (requestError) {
      // Put the unanswered question back so the conversation keeps alternating.
      setMessages(messages);
      setInput(question);
      setError(getErrorMessage(requestError, "The AI Doctor could not answer. Please try again."));
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

  function startOver() {
    setMessages([]);
    setInput("");
    setError("");
  }

  const offline = status && !status.llm_available;

  return (
    <>
      <PageHeader
        title="AI Doctor"
        subtitle="Ask about everyday health concerns like headache, cold, fever or stomach upset."
      >
        {messages.length > 0 && (
          <button type="button" className="text-button" onClick={startOver}>
            New conversation
          </button>
        )}
      </PageHeader>

      <section className="panel doctor-panel" aria-label="AI Doctor chat">
        <div className="doctor-notice" role="note">
          <Icon name="alert" size={18} />
          <p>
            <strong>General health information, not a diagnosis.</strong> I'm an AI and can't
            examine you. In an emergency (chest pain, trouble breathing, heavy bleeding, stroke
            signs) call your local emergency number now. Please don't enter your name or contact
            details.
          </p>
        </div>

        <div className="doctor-messages" ref={listRef} aria-live="polite">
          <div className="chatbot-message chatbot-assistant">{WELCOME}</div>

          {offline && (
            <div className="chatbot-note">
              The AI model isn't connected right now, so I can answer common everyday topics with
              built-in guidance.
            </div>
          )}

          {messages.length === 0 && (
            <div className="doctor-starters">
              <p>Try one of these, or type your own question:</p>
              <div>
                {STARTERS.map((starter) => (
                  <button key={starter.label} type="button" onClick={() => send(starter.text)} disabled={sending}>
                    {starter.label}
                  </button>
                ))}
              </div>
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
                      : "Built-in guidance"}
                </span>
              )}
            </div>
          ))}

          {sending && <div className="chatbot-message chatbot-assistant chatbot-typing">Thinking…</div>}

          {error && <div className="chatbot-error">{error}</div>}
        </div>

        <form
          className="doctor-input"
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
            placeholder="Describe your symptoms or ask a health question…"
            maxLength={4000}
            aria-label="Your health question"
          />
          <button type="submit" className="primary-button" disabled={sending || !input.trim()}>
            <Icon name="arrowRight" size={18} />
            <span>Send</span>
          </button>
        </form>
      </section>
    </>
  );
}
