"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { IconBuildingEstate, IconSearch, IconEdit } from "@tabler/icons-react";
import { UrlInput } from "@/components/url-input";
import { ManualInput } from "@/components/manual-input";
import { ValuationReport } from "@/components/valuation-report";
import { LoadingState } from "@/components/loading-state";
import { ErrorState } from "@/components/error-state";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AppState = "empty" | "loading" | "success" | "error";
type InputMode = "url" | "manual";

export interface ReportData {
  listing: {
    price_eur: number;
    city: string;
    neighborhood: string;
    size_m2: number;
    year_built?: number;
    floor?: number;
    description_summary?: string;
  };
  truth_score: number;
  negotiation_lever: string;
  avg_gurs_price_per_m2: number;
  asking_price_per_m2: number;
  num_comps: number;
  confidence: string;
  comps: Array<{
    transaction_date: string;
    neighborhood: string;
    size_m2: number;
    price_eur: number;
    price_per_m2: number;
    year_built?: number;
    floor?: number;
  }>;
  trend: Array<{
    month: string;
    avg_price_m2: number;
    num_transactions: number;
  }>;
  cached: boolean;
  // Wider area score
  wider_truth_score: number | null;
  wider_negotiation_lever: string | null;
  wider_avg_gurs_price_per_m2: number | null;
  wider_num_comps: number | null;
  wider_confidence: string | null;
  wider_comps: Array<{
    transaction_date: string;
    neighborhood: string;
    size_m2: number;
    price_eur: number;
    price_per_m2: number;
    year_built?: number;
    floor?: number;
  }> | null;
  wider_neighborhoods: string[] | null;
}

export default function Home() {
  const [state, setState] = useState<AppState>("empty");
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string>("");
  const [inputMode, setInputMode] = useState<InputMode>("url");

  async function analyzeUrl(url: string) {
    setState("loading");
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analiza ni uspela");
      }
      const data = await res.json();
      setReport(data);
      setState("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nekaj je šlo narobe");
      setState("error");
    }
  }

  async function analyzeManual(data: {
    price_eur: number;
    neighborhood: string;
    size_m2: number;
    year_built?: number;
    floor?: number;
  }) {
    setState("loading");
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manual: data }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analiza ni uspela");
      }
      const reportData = await res.json();
      setReport(reportData);
      setState("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nekaj je šlo narobe");
      setState("error");
    }
  }

  function reset() {
    setState("empty");
    setReport(null);
    setError("");
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-neutral-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-accent rounded-xl flex items-center justify-center">
              <IconBuildingEstate size={20} className="text-white" />
            </div>
            <div>
              <h1 className="font-heading text-xl font-bold tracking-tight text-neutral-950">
                Vrednost Nepremičnin
              </h1>
            </div>
          </div>
          {state === "success" && (
            <button
              onClick={reset}
              className="px-4 py-2 text-sm font-semibold rounded-full bg-transparent border border-neutral-950 text-neutral-950 hover:bg-neutral-50 transition-all active:scale-95"
            >
              Nova analiza
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-6">
        {state === "empty" && (
          <section className="py-16 sm:py-24">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-center max-w-2xl mx-auto"
            >
              <span className="px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-full bg-brand-accent/10 text-brand-accent inline-block">
                GURS podatki
              </span>
              <h2 className="mt-6 font-heading text-[clamp(2rem,5vw,2.75rem)] font-bold tracking-tight leading-none text-neutral-950">
                Preverite realno vrednost nepremičnine
              </h2>
              <p className="mt-4 font-sans text-lg leading-relaxed text-neutral-600">
                Primerjajte oglaševane cene z dejanskimi zaključnimi cenami iz
                GURS evidence trga nepremičnin.
              </p>
            </motion.div>

            {/* Input mode toggle */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="mt-10 max-w-2xl mx-auto"
            >
              <div className="flex gap-2 mb-6 justify-center">
                <button
                  onClick={() => setInputMode("url")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-full transition-all active:scale-95 ${
                    inputMode === "url"
                      ? "bg-neutral-950 text-white"
                      : "bg-transparent border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
                  }`}
                >
                  <IconSearch size={16} />
                  Vnesi povezavo
                </button>
                <button
                  onClick={() => setInputMode("manual")}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-full transition-all active:scale-95 ${
                    inputMode === "manual"
                      ? "bg-neutral-950 text-white"
                      : "bg-transparent border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
                  }`}
                >
                  <IconEdit size={16} />
                  Ročni vnos
                </button>
              </div>

              {inputMode === "url" ? (
                <UrlInput onSubmit={analyzeUrl} />
              ) : (
                <ManualInput onSubmit={analyzeManual} />
              )}
            </motion.div>
          </section>
        )}

        {state === "loading" && (
          <section className="py-16 sm:py-24">
            <LoadingState />
          </section>
        )}

        {state === "error" && (
          <section className="py-16 sm:py-24">
            <ErrorState message={error} onRetry={reset} />
          </section>
        )}

        {state === "success" && report && (
          <section className="py-10">
            <ValuationReport report={report} onNewAnalysis={reset} />
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-neutral-100 bg-neutral-50 py-6">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="font-sans text-sm text-neutral-500">
            Vir podatkov: GURS ETN (Evidenca trga nepremičnin). Samo za informativne namene.
          </p>
        </div>
      </footer>
    </div>
  );
}
