"use client";

import { useState } from "react";
import { IconArrowRight } from "@tabler/icons-react";

interface UrlInputProps {
  onSubmit: (url: string) => void;
}

export function UrlInput({ onSubmit }: UrlInputProps) {
  const [url, setUrl] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim());
    }
  }

  return (
    <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="url"
            placeholder="https://www.nepremicnine.net/oglasi-prodaja/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full px-3.5 py-3 bg-neutral-50 border border-neutral-200 rounded-xl outline-none focus:ring-2 focus:ring-brand-accent transition-all font-sans text-lg"
          />
          <p className="mt-2 font-sans text-sm text-neutral-500">
            Prilepite povezavo oglasa z nepremicnine.net
          </p>
        </div>
        <button
          type="submit"
          disabled={!url.trim()}
          className="w-full flex items-center justify-center gap-2 px-5 py-3 text-base font-semibold rounded-full bg-neutral-950 text-white hover:bg-brand-accent transition-all active:scale-95 hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          Preveri ceno
          <IconArrowRight size={18} />
        </button>
      </form>
    </div>
  );
}
