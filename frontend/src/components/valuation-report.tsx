"use client";

import { motion } from "framer-motion";
import {
  IconTrendingUp,
  IconTrendingDown,
  IconEqual,
  IconInfoCircle,
} from "@tabler/icons-react";
import { TrendSparkline } from "@/components/trend-sparkline";
import type { ReportData } from "@/app/page";

interface ValuationReportProps {
  report: ReportData;
  onNewAnalysis: () => void;
}

function formatEur(n: number): string {
  return new Intl.NumberFormat("sl-SI", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function getScoreColor(score: number): string {
  if (score > 10) return "text-red-600";
  if (score > 0) return "text-orange-500";
  if (score > -10) return "text-green-600";
  return "text-emerald-700";
}

function getScoreBg(score: number): string {
  if (score > 10) return "bg-red-50 border-red-200";
  if (score > 0) return "bg-orange-50 border-orange-200";
  if (score > -10) return "bg-green-50 border-green-200";
  return "bg-emerald-50 border-emerald-200";
}

function getScoreIcon(score: number) {
  if (score > 5) return <IconTrendingUp size={28} />;
  if (score < -5) return <IconTrendingDown size={28} />;
  return <IconEqual size={28} />;
}

function getConfidenceLabel(confidence: string): string {
  switch (confidence) {
    case "high":
      return "Visoka zanesljivost";
    case "medium":
      return "Srednja zanesljivost";
    default:
      return "Nizka zanesljivost";
  }
}

export function ValuationReport({
  report,
  onNewAnalysis,
}: ValuationReportProps) {
  const { listing, truth_score, comps, trend } = report;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Truth Score Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div
          className={`border-2 rounded-2xl p-8 sm:p-10 text-center ${getScoreBg(truth_score)}`}
        >
          <div
            className={`inline-flex items-center gap-2 ${getScoreColor(truth_score)}`}
          >
            {getScoreIcon(truth_score)}
            <span className="font-heading text-[clamp(2.5rem,8vw,4rem)] font-bold tracking-tight leading-none">
              {Math.abs(truth_score).toFixed(0)}%
            </span>
          </div>
          <p
            className={`mt-2 font-heading text-xl font-bold ${getScoreColor(truth_score)}`}
          >
            {truth_score > 0
              ? "nad povprečjem"
              : truth_score < 0
                ? "pod povprečjem"
                : "v okviru povprečja"}
          </p>
          <p className="mt-3 font-sans text-base leading-relaxed text-neutral-600 max-w-xl mx-auto">
            {report.num_comps > 0 ? (
              <>
                Oglaševana cena{" "}
                <span className="font-semibold text-neutral-950">
                  {formatEur(report.asking_price_per_m2)} EUR/m²
                </span>{" "}
                je{" "}
                {truth_score > 0
                  ? "višja"
                  : truth_score < 0
                    ? "nižja"
                    : "enaka"}{" "}
                od povprečne zaključne cene{" "}
                <span className="font-semibold text-neutral-950">
                  {formatEur(report.avg_gurs_price_per_m2)} EUR/m²
                </span>{" "}
                za nedavne prodaje v četrti{" "}
                <span className="font-semibold text-neutral-950">
                  {listing.neighborhood}
                </span>
                .
              </>
            ) : (
              `Premalo podatkov o transakcijah za ${listing.neighborhood} za primerjavo.`
            )}
          </p>
          <div className="mt-4 flex items-center justify-center gap-2 flex-wrap">
            <span className="px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-full bg-neutral-950/10 text-neutral-700 inline-block">
              {getConfidenceLabel(report.confidence)}
            </span>
            {report.num_comps > 0 && (
              <span className="px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-full bg-neutral-950/5 text-neutral-500 inline-block">
                Na podlagi {report.num_comps} prodaj
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Negotiation Lever */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8">
          <h3 className="font-heading text-lg font-bold tracking-tight text-neutral-950 flex items-center gap-2">
            <IconInfoCircle size={20} className="text-brand-accent" />
            Pogajalski vzvod
          </h3>
          <p className="mt-3 font-sans text-base leading-relaxed text-neutral-600">
            {report.negotiation_lever}
          </p>
        </div>
      </motion.div>

      {/* Key Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="grid grid-cols-2 sm:grid-cols-4 gap-4"
      >
        {[
          {
            label: "Oglaševana cena/m²",
            value: `${formatEur(report.asking_price_per_m2)}`,
          },
          {
            label: "GURS povprečje/m²",
            value: `${formatEur(report.avg_gurs_price_per_m2)}`,
          },
          { label: "Primerljive prodaje", value: `${report.num_comps}` },
          { label: "Velikost", value: `${listing.size_m2} m²` },
        ].map((metric, i) => (
          <div
            key={metric.label}
            className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-5 text-center"
          >
            <p className="font-sans text-sm text-neutral-500">{metric.label}</p>
            <p className="mt-1 font-heading text-2xl font-bold tracking-tight text-neutral-950">
              {metric.value}
            </p>
          </div>
        ))}
      </motion.div>

      {/* Listing Details */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8">
          <h3 className="font-heading text-lg font-bold tracking-tight text-neutral-950">
            Podrobnosti oglasa
          </h3>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <dt className="font-sans text-sm text-neutral-500">Lokacija</dt>
              <dd className="font-sans text-base font-semibold text-neutral-950">
                {listing.neighborhood}, {listing.city}
              </dd>
            </div>
            <div>
              <dt className="font-sans text-sm text-neutral-500">Cena</dt>
              <dd className="font-sans text-base font-semibold text-neutral-950">
                {formatEur(listing.price_eur)} EUR
              </dd>
            </div>
            {listing.year_built && (
              <div>
                <dt className="font-sans text-sm text-neutral-500">
                  Leto izgradnje
                </dt>
                <dd className="font-sans text-base font-semibold text-neutral-950">
                  {listing.year_built}
                </dd>
              </div>
            )}
            {listing.floor != null && (
              <div>
                <dt className="font-sans text-sm text-neutral-500">
                  Nadstropje
                </dt>
                <dd className="font-sans text-base font-semibold text-neutral-950">
                  {listing.floor}
                </dd>
              </div>
            )}
            {listing.description_summary && (
              <div className="col-span-2">
                <dt className="font-sans text-sm text-neutral-500">Opis</dt>
                <dd className="font-sans text-base text-neutral-700">
                  {listing.description_summary}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </motion.div>

      {/* Price Trend */}
      {trend.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8">
            <h3 className="font-heading text-lg font-bold tracking-tight text-neutral-950">
              Gibanje cen — {listing.neighborhood}
            </h3>
            <div className="mt-4">
              <TrendSparkline data={trend} />
            </div>
          </div>
        </motion.div>
      )}

      {/* Comparable Transactions */}
      {comps.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 }}
        >
          <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8 overflow-hidden">
            <h3 className="font-heading text-lg font-bold tracking-tight text-neutral-950">
              Primerljive transakcije ({comps.length})
            </h3>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-neutral-100">
                    <th className="pb-3 font-sans text-sm font-semibold text-neutral-500">
                      Datum
                    </th>
                    <th className="pb-3 font-sans text-sm font-semibold text-neutral-500">
                      Četrt
                    </th>
                    <th className="pb-3 font-sans text-sm font-semibold text-neutral-500 text-right">
                      Velikost
                    </th>
                    <th className="pb-3 font-sans text-sm font-semibold text-neutral-500 text-right">
                      Cena
                    </th>
                    <th className="pb-3 font-sans text-sm font-semibold text-neutral-500 text-right">
                      EUR/m²
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comps.map((comp, i) => (
                    <tr
                      key={i}
                      className="border-b border-neutral-50 last:border-0"
                    >
                      <td className="py-3 font-sans text-sm text-neutral-700">
                        {comp.transaction_date}
                      </td>
                      <td className="py-3 font-sans text-sm text-neutral-700">
                        {comp.neighborhood}
                      </td>
                      <td className="py-3 font-sans text-sm text-neutral-700 text-right">
                        {comp.size_m2} m²
                      </td>
                      <td className="py-3 font-sans text-sm text-neutral-700 text-right">
                        {formatEur(comp.price_eur)} EUR
                      </td>
                      <td className="py-3 font-sans text-sm font-semibold text-neutral-950 text-right">
                        {formatEur(comp.price_per_m2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}

      {/* Low confidence warning */}
      {report.num_comps > 0 && report.num_comps < 3 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.6 }}
        >
          <div className="bg-brand-accent-light border border-brand-accent/20 rounded-2xl p-5 text-center">
            <p className="font-sans text-sm text-brand-accent font-semibold">
              Na podlagi samo {report.num_comps} transakcij(e). Rezultati morda
              niso reprezentativni. Poskusite razširiti iskalno območje.
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
