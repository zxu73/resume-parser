import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { ChatSuggestion, ChatMessage } from '../types/analysis';

interface ChatBotProps {
  resumeText: string;
  jobDescription: string;
  onAddSuggestion: (suggestion: ChatSuggestion) => void;
  docId?: string;
  onDocUpdated?: (newDocId: string) => void;
}

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: ChatSuggestion[];
}

export const ChatBot: React.FC<ChatBotProps> = ({ resumeText, jobDescription, onAddSuggestion, docId, onDocUpdated }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([
    {
      role: 'assistant',
      content: "Hi! I'm your resume improvement assistant. Tell me what you'd like to improve — for example: \"Make my Python bullet more impactful\" or \"I want to emphasize my leadership experience more.\"",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [addedSuggestions, setAddedSuggestions] = useState<Set<string>>(new Set());
  const [appliedKeys, setAppliedKeys] = useState<Set<string>>(new Set());
  const [skippedKeys, setSkippedKeys] = useState<Set<string>>(new Set());
  const [applyingKey, setApplyingKey] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const historyForApi = (): ChatMessage[] =>
    messages
      .filter((m) => m.role !== 'assistant' || messages.indexOf(m) > 0) // skip the initial greeting
      .map((m) => ({ role: m.role, content: m.content }));

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: DisplayMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_history: historyForApi(),
          resume_text: resumeText,
          job_description: jobDescription,
        }),
      });

      if (!res.ok) throw new Error('Chat request failed');
      const data = await res.json();

      const assistantMsg: DisplayMessage = {
        role: 'assistant',
        content: data.reply || 'Here are my suggestions.',
        suggestions: data.suggestions ?? [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleAddSuggestion = (suggestion: ChatSuggestion) => {
    const key = suggestion.current_text + suggestion.suggested_text;
    if (addedSuggestions.has(key)) return;
    setAddedSuggestions((prev) => new Set([...prev, key]));
    onAddSuggestion(suggestion);
  };

  const handleApprove = async (sug: ChatSuggestion) => {
    const key = sug.current_text + sug.suggested_text;
    if (!docId || appliedKeys.has(key) || applyingKey === key) return;
    setApplyingKey(key);
    try {
      const res = await fetch('/apply-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId,
          replacements: [{ current_text: sug.current_text, suggested_text: sug.suggested_text }],
        }),
      });
      if (!res.ok) throw new Error('Apply failed');
      const data = await res.json();
      if (data.success) {
        setAppliedKeys((prev) => new Set([...prev, key]));
        onDocUpdated?.(data.doc_id);
      }
    } catch {
      // leave button in normal state so user can retry
    } finally {
      setApplyingKey(null);
    }
  };

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 1000,
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: isOpen ? '#374151' : '#2563eb',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
          fontSize: '22px',
          transition: 'background 0.2s',
        }}
        title={isOpen ? 'Close chat' : 'Chat with AI'}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px',
            right: '24px',
            width: '380px',
            maxHeight: '540px',
            zIndex: 999,
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: '#2563eb',
              color: '#fff',
              padding: '12px 16px',
              fontWeight: 700,
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>💬</span>
            <span>BetterCV Assistant</span>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            {messages.map((msg, i) => (
              <div key={i}>
                {/* Bubble */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '88%',
                      padding: '9px 13px',
                      borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                      background: msg.role === 'user' ? '#2563eb' : '#f3f4f6',
                      color: msg.role === 'user' ? '#fff' : '#111827',
                      fontSize: '13px',
                      lineHeight: '1.5',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.content}
                  </div>
                </div>

                {/* Suggestion cards (below assistant messages) */}
                {msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {msg.suggestions.map((sug, j) => {
                      const key = sug.current_text + sug.suggested_text;
                      const alreadyAdded = addedSuggestions.has(key);
                      return (
                        <div
                          key={j}
                          style={{
                            background: '#f9fafb',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '10px 12px',
                            fontSize: '12px',
                          }}
                        >
                          <div style={{ color: '#dc2626', fontWeight: 600, marginBottom: '4px' }}>
                            Before
                          </div>
                          <div
                            style={{
                              background: '#fef2f2',
                              border: '1px solid #fecaca',
                              borderRadius: '6px',
                              padding: '6px 8px',
                              color: '#991b1b',
                              marginBottom: '8px',
                              lineHeight: 1.45,
                            }}
                          >
                            "{sug.current_text}"
                          </div>
                          <div style={{ color: '#16a34a', fontWeight: 600, marginBottom: '4px' }}>
                            After
                          </div>
                          <div
                            style={{
                              background: '#f0fdf4',
                              border: '1px solid #bbf7d0',
                              borderRadius: '6px',
                              padding: '6px 8px',
                              color: '#166534',
                              marginBottom: '8px',
                              lineHeight: 1.45,
                            }}
                          >
                            "{sug.suggested_text}"
                          </div>
                          {sug.reason && (
                            <div style={{ color: '#6b7280', marginBottom: '8px', fontStyle: 'italic' }}>
                              {sug.reason}
                            </div>
                          )}
                          <button
                            onClick={() => handleAddSuggestion(sug)}
                            disabled={alreadyAdded}
                            style={{
                              width: '100%',
                              padding: '6px 10px',
                              borderRadius: '6px',
                              border: 'none',
                              background: alreadyAdded ? '#d1fae5' : '#2563eb',
                              color: alreadyAdded ? '#065f46' : '#fff',
                              fontWeight: 600,
                              fontSize: '12px',
                              cursor: alreadyAdded ? 'default' : 'pointer',
                              transition: 'background 0.15s',
                            }}
                          >
                            {alreadyAdded ? 'Added to Review ✓' : 'Add to Review'}
                          </button>

                          {/* Approve / Skip — only when a live document is loaded */}
                          {docId && (() => {
                            const isApplied = appliedKeys.has(key);
                            const isSkipped = skippedKeys.has(key);
                            const isApplying = applyingKey === key;
                            return (
                              <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                                <button
                                  onClick={() => handleApprove(sug)}
                                  disabled={isApplied || isSkipped || isApplying}
                                  style={{
                                    flex: 1,
                                    padding: '6px 8px',
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: isApplied ? '#d1fae5' : '#16a34a',
                                    color: isApplied ? '#065f46' : '#fff',
                                    fontWeight: 600,
                                    fontSize: '12px',
                                    cursor: (isApplied || isSkipped || isApplying) ? 'default' : 'pointer',
                                    transition: 'background 0.15s',
                                    opacity: isSkipped ? 0.4 : 1,
                                  }}
                                >
                                  {isApplying ? 'Applying…' : isApplied ? 'Applied ✓' : 'Approve'}
                                </button>
                                <button
                                  onClick={() => setSkippedKeys((prev) => new Set([...prev, key]))}
                                  disabled={isApplied || isSkipped}
                                  style={{
                                    flex: 1,
                                    padding: '6px 8px',
                                    borderRadius: '6px',
                                    border: '1px solid #d1d5db',
                                    background: isSkipped ? '#f3f4f6' : '#fff',
                                    color: '#374151',
                                    fontWeight: 600,
                                    fontSize: '12px',
                                    cursor: (isApplied || isSkipped) ? 'default' : 'pointer',
                                    opacity: (isApplied || isSkipped) ? 0.5 : 1,
                                  }}
                                >
                                  {isSkipped ? 'Skipped' : 'Skip'}
                                </button>
                              </div>
                            );
                          })()}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div
                  style={{
                    padding: '9px 13px',
                    borderRadius: '14px 14px 14px 4px',
                    background: '#f3f4f6',
                    color: '#6b7280',
                    fontSize: '13px',
                  }}
                >
                  Thinking…
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div
            style={{
              borderTop: '1px solid #e5e7eb',
              padding: '10px 12px',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-end',
              background: '#fff',
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask how to improve your resume…"
              rows={2}
              style={{
                flex: 1,
                resize: 'none',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                padding: '8px 10px',
                fontSize: '13px',
                lineHeight: '1.4',
                outline: 'none',
                fontFamily: 'inherit',
              }}
              disabled={isLoading}
            />
            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              style={{
                padding: '0 14px',
                height: '40px',
                background: '#2563eb',
                color: '#fff',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              Send
            </Button>
          </div>
        </div>
      )}
    </>
  );
};
