"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UrlInput } from "@/components/url-input";
import { ManualInput } from "@/components/manual-input";
import { ValuationReport } from "@/components/valuation-report";
import { LoadingState } from "@/components/loading-state";
import { ErrorState } from "@/components/error-state";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AppState = "empty" | "loading" | "success" | "error";

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
}

export default function Home() {
  const [state, setState] = useState<AppState>("empty");
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string>("");

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
        throw new Error(err.detail || "Analysis failed");
      }
      const data = await res.json();
      setReport(data);
      setState("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
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
        throw new Error(err.detail || "Analysis failed");
      }
      const reportData = await res.json();
      setReport(reportData);
      setState("success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setState("error");
    }
  }

  function reset() {
    setState("empty");
    setReport(null);
    setError("");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-4xl px-4 py-6">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Vrednost Nepremičnin
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Compare asking prices against actual GURS transaction data
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {state === "empty" && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-gray-900">
                Check the truth about any listing
              </h2>
              <p className="mt-2 text-lg text-gray-600">
                Paste a nepremicnine.net URL or enter details manually
              </p>
            </div>

            <Tabs defaultValue="url" className="mx-auto max-w-2xl">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="url">Paste URL</TabsTrigger>
                <TabsTrigger value="manual">Manual Entry</TabsTrigger>
              </TabsList>
              <TabsContent value="url" className="mt-4">
                <UrlInput onSubmit={analyzeUrl} />
              </TabsContent>
              <TabsContent value="manual" className="mt-4">
                <ManualInput onSubmit={analyzeManual} />
              </TabsContent>
            </Tabs>
          </div>
        )}

        {state === "loading" && <LoadingState />}
        {state === "error" && <ErrorState message={error} onRetry={reset} />}
        {state === "success" && report && (
          <ValuationReport report={report} onNewAnalysis={reset} />
        )}
      </main>

      <footer className="mt-auto border-t bg-white py-4">
        <div className="mx-auto max-w-4xl px-4 text-center text-xs text-gray-400">
          Data source: GURS ETN (Evidenca trga nepremičnin). For informational
          purposes only.
        </div>
      </footer>
    </div>
  );
}
