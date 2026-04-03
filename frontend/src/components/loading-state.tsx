"use client";

import { Card, CardContent } from "@/components/ui/card";

export function LoadingState() {
  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-gray-900" />
          <p className="mt-4 text-lg font-medium text-gray-900">
            Analyzing listing...
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Scraping data and matching against GURS transactions
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
