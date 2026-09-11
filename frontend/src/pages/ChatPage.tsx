import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type {
  Conversation,
  ConversationDetail,
  Message,
  Repository,
} from "../api/types";
import { useToast } from "../context/ToastContext";
import { EmptyState, Spinner, formatDate } from "../components/ui";

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
          isUser ? "bg-brand-600 text-white" : "border border-slate-200 bg-white text-slate-700"
        }`}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        {!isUser && (
          <>
            {message.citations.length > 0 && (
              <div className="mt-3 border-t border-slate-100 pt-2">
                <p className="text-xs font-semibold text-slate-500">Fuentes citadas:</p>
                <ul className="mt-1 space-y-1.5">
                  {message.citations.map((c, i) => (
                    <li key={c.id} className="rounded-lg bg-slate-50 p-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <Link
                          to={`/documentos/${c.document_id}`}
                          className="font-medium text-brand-700 hover:underline"
                        >
                          [Fuente {i + 1}] {c.document_name}
                        </Link>
                        <span className="shrink-0 text-slate-400">
                          pág. {c.page_number} · {(c.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-3 text-slate-500">{c.snippet}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!message.grounded && (
              <p className="mt-2 rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-700">
                Sin evidencia suficiente en los documentos — la respuesta no inventa información.
              </p>
            )}
            <p className="mt-2 text-[10px] text-slate-400">
              {message.model} · {message.latency_ms} ms · {message.chunk_count} fragmentos
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { notify } = useToast();
  const [searchParams] = useSearchParams();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoId, setRepoId] = useState<string>(searchParams.get("repositorio") ?? "");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [current, setCurrent] = useState<ConversationDetail | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<Repository[]>("/repositories").then((r) => {
      setRepos(r.data);
      if (!repoId && r.data.length > 0) setRepoId(String(r.data[0].id));
    }).catch(() => undefined);
    // repoId intentionally omitted: only prime the default on first load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConversations = useCallback(() => {
    api.get<Conversation[]>("/conversations").then((r) => setConversations(r.data)).catch(() => undefined);
  }, []);

  useEffect(loadConversations, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [current?.messages.length]);

  async function openConversation(convId: number) {
    setLoadingConv(true);
    try {
      const resp = await api.get<ConversationDetail>(`/conversations/${convId}`);
      setCurrent(resp.data);
      setRepoId(String(resp.data.repository_id));
    } catch (err) {
      notify("error", errorMessage(err));
    } finally {
      setLoadingConv(false);
    }
  }

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (q.length < 3) return;
    if (!repoId) {
      notify("error", "Seleccione un repositorio primero");
      return;
    }
    setAsking(true);
    try {
      let conv = current;
      if (!conv || String(conv.repository_id) !== repoId) {
        const created = await api.post<Conversation>("/conversations", {
          repository_id: Number(repoId),
        });
        conv = { ...created.data, messages: [] };
        setCurrent(conv);
      }
      // Optimistic user message
      const optimistic: Message = {
        id: -1, role: "user", content: q, model: "", latency_ms: 0,
        chunk_count: 0, grounded: true, created_at: new Date().toISOString(), citations: [],
      };
      setCurrent((prev) => prev && { ...prev, messages: [...prev.messages, optimistic] });
      setQuestion("");
      const resp = await api.post<Message>(`/conversations/${conv.id}/ask`, { question: q });
      const refreshed = await api.get<ConversationDetail>(`/conversations/${conv.id}`);
      setCurrent(refreshed.data);
      loadConversations();
      void resp;
    } catch (err) {
      notify("error", errorMessage(err));
    } finally {
      setAsking(false);
    }
  }

  function newConversation() {
    setCurrent(null);
    setQuestion("");
  }

  return (
    <div className="grid gap-6 lg:grid-cols-4">
      <aside className="lg:col-span-1">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <label htmlFor="chat-repo" className="block text-sm font-medium text-slate-700">
            Repositorio a consultar
          </label>
          <select
            id="chat-repo"
            value={repoId}
            onChange={(e) => {
              setRepoId(e.target.value);
              setCurrent(null);
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {repos.length === 0 && <option value="">Sin repositorios</option>}
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <button
            onClick={newConversation}
            className="mt-3 w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Nueva conversación
          </button>
        </div>
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Historial</h2>
          {conversations.length === 0 ? (
            <p className="text-xs text-slate-400">Sin conversaciones aún</p>
          ) : (
            <ul className="max-h-80 space-y-1 overflow-y-auto">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => openConversation(c.id)}
                    className={`w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-slate-50 ${
                      current?.id === c.id ? "bg-brand-50 text-brand-700" : "text-slate-600"
                    }`}
                  >
                    <span className="line-clamp-2">{c.title}</span>
                    <span className="text-[10px] text-slate-400">{formatDate(c.updated_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      <section className="flex min-h-[70vh] flex-col rounded-xl border border-slate-200 bg-slate-50 lg:col-span-3">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {loadingConv ? (
            <Spinner />
          ) : !current || current.messages.length === 0 ? (
            <EmptyState
              title="Pregunte sobre sus documentos"
              hint='Ej: "¿Cuál es el valor total del contrato de servicios?" — la respuesta citará los documentos fuente'
            />
          ) : (
            current.messages.map((m, i) => <MessageBubble key={`${m.id}-${i}`} message={m} />)
          )}
          {asking && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-400">
                Analizando documentos...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={handleAsk} className="border-t border-slate-200 bg-white p-3">
          <div className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Escriba su pregunta..."
              aria-label="Pregunta sobre los documentos"
              maxLength={2000}
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={asking || question.trim().length < 3}
              className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Preguntar
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
