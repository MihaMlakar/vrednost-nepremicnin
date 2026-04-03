"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="mx-auto max-w-2xl">
      <Card className="border-red-200">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <span className="text-2xl">!</span>
          </div>
          <p className="mt-4 text-lg font-medium text-gray-900">
            Analysis failed
          </p>
          <p className="mt-1 text-sm text-gray-600">{message}</p>
          <Button onClick={onRetry} variant="outline" className="mt-6">
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
