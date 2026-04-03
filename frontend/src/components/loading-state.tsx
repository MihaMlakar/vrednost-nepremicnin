"use client";

import { motion } from "framer-motion";
import { IconLoader2 } from "@tabler/icons-react";

export function LoadingState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      <div className="bg-white border border-neutral-100 shadow-sm rounded-2xl p-12 text-center">
        <IconLoader2 size={48} className="mx-auto text-brand-accent animate-spin" />
        <p className="mt-4 font-heading text-xl font-bold tracking-tight text-neutral-950">
          Analiziramo oglas...
        </p>
        <p className="mt-2 font-sans text-base text-neutral-500">
          Pridobivamo podatke in primerjamo s transakcijami GURS
        </p>
      </div>
    </motion.div>
  );
}
