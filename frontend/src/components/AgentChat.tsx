'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useChatHistory, useSendChat } from '@/hooks/useChat';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Sparkles, User, Wand2 } from 'lucide-react';

interface AgentChatProps {
  tripId: string;
  onRunStarted?: (runId: string) => void;
  streamingText?: string;
  className?: string;
}

const SUGGESTION_CHIPS = [
  'Make Day 2 more relaxed',
  'Add a street-food stop',
  'Cut Rs 2000',
];

export function AgentChat({
  tripId,
  onRunStarted,
  streamingText,
  className = '',
}: AgentChatProps) {
  const { data: messages = [], isLoading } = useChatHistory(tripId);
  const { mutate: sendChat, isPending } = useSendChat(tripId);
  const [inputVal, setInputVal] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isPending]);

  const handleSend = (text: string) => {
    if (!text.trim() || isPending) return;
    setInputVal('');

    sendChat(text, {
      onSuccess: (data) => {
        if (data.run_id && onRunStarted) {
          onRunStarted(data.run_id);
        }
      },
    });
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages list */}
      <div className="flex-1 overflow-y-auto space-y-3.5 p-4 text-small">
        {messages.length === 0 && !isLoading && (
          <div className="p-6 text-center text-text-muted space-y-2">
            <div className="h-10 w-10 mx-auto rounded-full btn-primary-gradient flex items-center justify-center text-on-primary shadow-xs">
              <Sparkles size={20} strokeWidth={1.75} />
            </div>
            <p className="text-small font-medium text-text-secondary">
              Ask Reroute to tweak your schedule, shift stops, or recover budget.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar: assistant avatar as a gradient circle with a sparkles icon */}
              <div
                className={`h-8 w-8 rounded-full shrink-0 flex items-center justify-center shadow-xs ${
                  isUser
                    ? 'bg-surface-alt text-text-primary'
                    : 'btn-primary-gradient text-on-primary'
                }`}
              >
                {isUser ? (
                  <User size={16} strokeWidth={1.75} />
                ) : (
                  <Sparkles size={16} strokeWidth={1.75} />
                )}
              </div>

              {/* Message Bubble: user in primary, assistant in tinted surface */}
              <div
                className={`max-w-[85%] rounded-[14px] px-3.5 py-2.5 text-small leading-relaxed shadow-xs ${
                  isUser
                    ? 'btn-primary-gradient text-on-primary font-medium'
                    : 'card-surface text-text-primary'
                }`}
              >
                {msg.content}
              </div>
            </div>
          );
        })}

        {streamingText && (
          <div className="flex items-start gap-2.5">
            <div className="h-8 w-8 rounded-full shrink-0 btn-primary-gradient text-on-primary flex items-center justify-center shadow-xs">
              <Sparkles size={16} strokeWidth={1.75} />
            </div>
            <div className="max-w-[85%] rounded-[14px] px-3.5 py-2.5 text-small leading-relaxed shadow-xs card-surface text-text-primary whitespace-pre-wrap">
              {streamingText}
            </div>
          </div>
        )}

        {isPending && !streamingText && (
          <div className="flex items-start gap-2.5">
            <div className="h-8 w-8 rounded-full shrink-0 btn-primary-gradient text-on-primary flex items-center justify-center">
              <Sparkles size={16} strokeWidth={1.75} />
            </div>
            <div className="card-surface px-3.5 py-2.5 text-text-secondary animate-pulse text-small">
              Evaluating plan constraints and researching alternatives...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips with Wand icon */}
      <div className="px-4 py-2 border-t border-border flex flex-wrap gap-1.5">
        {SUGGESTION_CHIPS.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => handleSend(chip)}
            className="text-caption px-3 py-1.5 rounded-pill bg-surface-alt hover:bg-primary/10 hover:text-primary transition-colors text-text-secondary flex items-center gap-1.5 border border-border"
          >
            <Wand2 size={16} strokeWidth={1.75} className="text-primary" />
            <span>{chip}</span>
          </button>
        ))}
      </div>

      {/* Input Row */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(inputVal);
        }}
        className="p-3 sm:p-4 border-t border-border flex items-center gap-2"
      >
        <Input
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Ask Reroute anything..."
          className="text-small"
          disabled={isPending}
        />
        <Button
          type="submit"
          size="icon-sm"
          disabled={!inputVal.trim() || isPending}
          aria-label="Send message to Reroute"
          className="shrink-0"
        >
          <Send size={16} strokeWidth={1.75} />
        </Button>
      </form>
    </div>
  );
}
