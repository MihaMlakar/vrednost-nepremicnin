"use client";

import { motion } from "framer-motion";
import { IconAlertTriangle } from "@tabler/icons-react";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      <div className="bg-white border border-red-200 shadow-sm rounded-2xl p-12 text-center">
        <div className="w-12 h-12 mx-auto bg-red-100 rounded-full flex items-center justify-center">
          <IconAlertTriangle size={24} className="text-red-600" />
        </div>
        <p className="mt-4 font-heading text-xl font-bold tracking-tight text-neutral-950">
          Analiza ni uspela
        </p>
        <p className="mt-2 font-sans text-base text-neutral-600">{message}</p>
        <button
          onClick={onRetry}
          className="mt-6 px-4 py-2 text-sm font-semibold rounded-full bg-transparent border border-neutral-950 text-neutral-950 hover:bg-neutral-50 transition-all active:scale-95"
        >
          Poskusite znova
        </button>
      </div>
    </motion.div>
  );
}
