"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

const NEIGHBORHOODS = [
  "Bežigrad", "Center", "Črnuče", "Dravlje", "Fužine",
  "Jarše", "Kodeljevo", "Moste", "Polje", "Rožna dolina",
  "Rudnik", "Šentvid", "Šiška", "Trnovo", "Vič",
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

  return (
    <Card>
      <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Asking Price (EUR) *
              </label>
              <Input
                type="number"
                placeholder="185000"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                min={10000}
                max={5000000}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">
                Size (m²) *
              </label>
              <Input
                type="number"
                placeholder="55"
                value={size}
                onChange={(e) => setSize(e.target.value)}
                min={10}
                max={500}
                step={0.1}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              Neighborhood *
            </label>
            <select
              value={neighborhood}
              onChange={(e) => setNeighborhood(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            >
              <option value="">Select neighborhood...</option>
              {NEIGHBORHOODS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Year Built
              </label>
              <Input
                type="number"
                placeholder="1985"
                value={yearBuilt}
                onChange={(e) => setYearBuilt(e.target.value)}
                min={1800}
                max={2026}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">
                Floor
              </label>
              <Input
                type="number"
                placeholder="3"
                value={floor}
                onChange={(e) => setFloor(e.target.value)}
                min={0}
                max={30}
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-12 text-lg font-semibold"
            disabled={!isValid}
          >
            Check Truth
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
