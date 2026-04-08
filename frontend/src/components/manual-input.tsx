"use client";

import { useState } from "react";
import { IconArrowRight } from "@tabler/icons-react";

const NEIGHBORHOODS = [
  "Bežigrad", "Center", "Črnuče", "Dravlje", "Fužine",
  "Jarše", "Ježica", "Kodeljevo", "Koseze", "Moste",
  "Murgle", "Polje", "Rožna dolina", "Rudnik", "Šentvid",
  "Šiška", "Štepanjsko naselje", "Trnovo", "Vič", "Zelena jama",
];

interface ManualInputProps {
  onSubmit: (data: {
    price_eur: number;
    neighborhood: string;
    size_m2: number;
    year_built?: number;
    floor?: number;
  }) => void;
}

export function ManualInput({ onSubmit }: ManualInputProps) {
  const [price, setPrice] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [size, setSize] = useState("");
  const [yearBuilt, setYearBuilt] = useState("");
  const [floor, setFloor] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (price && neighborhood && size) {
      onSubmit({
        price_eur: parseFloat(price),
        neighborhood,
        size_m2: parseFloat(size),
        year_built: yearBuilt ? parseInt(yearBuilt) : undefined,
        floor: floor ? parseInt(floor) : undefined,
      });
    }
  }

  const isValid = price && neighborhood && size;
  const inputClass =
    "w-full px-3.5 py-2.5 bg-neutral-50 border border-neutral-200 rounded-xl outline-none focus:ring-2 focus:ring-brand-accent transition-all font-sans text-lg";

  return (
    <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-8">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="font-sans text-sm font-semibold text-neutral-950">
              Oglaševana cena (EUR) *
            </label>
            <input
              type="number"
              placeholder="185000"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              min={10000}
              max={5000000}
              className={inputClass}
            />
          </div>
          <div>
            <label className="font-sans text-sm font-semibold text-neutral-950">
              Velikost (m²) *
            </label>
            <input
              type="number"
              placeholder="55"
              value={size}
              onChange={(e) => setSize(e.target.value)}
              min={10}
              max={500}
              step={0.1}
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label className="font-sans text-sm font-semibold text-neutral-950">
            Četrt *
          </label>
          <select
            value={neighborhood}
            onChange={(e) => setNeighborhood(e.target.value)}
            className={inputClass}
          >
            <option value="">Izberite četrt...</option>
            {NEIGHBORHOODS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="font-sans text-sm font-semibold text-neutral-950">
              Leto izgradnje
            </label>
            <input
              type="number"
              placeholder="1985"
              value={yearBuilt}
              onChange={(e) => setYearBuilt(e.target.value)}
              min={1800}
              max={2026}
              className={inputClass}
            />
          </div>
          <div>
            <label className="font-sans text-sm font-semibold text-neutral-950">
              Nadstropje
            </label>
            <input
              type="number"
              placeholder="3"
              value={floor}
              onChange={(e) => setFloor(e.target.value)}
              min={0}
              max={30}
              className={inputClass}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={!isValid}
          className="w-full flex items-center justify-center gap-2 px-5 py-3 text-base font-semibold rounded-full bg-neutral-950 text-white hover:bg-brand-accent transition-all active:scale-95 hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          Preveri ceno
          <IconArrowRight size={18} />
        </button>
      </form>
    </div>
  );
}
