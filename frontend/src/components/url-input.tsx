"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

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
    <Card>
      <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Input
              type="url"
              placeholder="https://www.nepremicnine.net/oglasi-prodaja/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="text-lg h-12"
            />
            <p className="mt-1.5 text-xs text-gray-500">
              Paste a listing URL from nepremicnine.net
            </p>
          </div>
          <Button
            type="submit"
            className="w-full h-12 text-lg font-semibold"
            disabled={!url.trim()}
          >
            Check Truth
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
