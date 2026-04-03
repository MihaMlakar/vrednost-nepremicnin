"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

function getScoreLabel(score: number): string {
  if (score > 15) return "Significantly Overpriced";
  if (score > 5) return "Above Average";
  if (score > -5) return "Fair Price";
  if (score > -15) return "Good Deal";
  return "Significantly Underpriced";
}

function getConfidenceBadge(confidence: string) {
  switch (confidence) {
    case "high":
      return <Badge variant="default">High Confidence</Badge>;
    case "medium":
      return <Badge variant="secondary">Medium Confidence</Badge>;
    default:
      return <Badge variant="outline">Low Confidence</Badge>;
  }
}

export function ValuationReport({ report, onNewAnalysis }: ValuationReportProps) {
  const { listing, truth_score, comps, trend } = report;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Button variant="outline" onClick={onNewAnalysis} size="sm">
        New Analysis
      </Button>

      {/* Truth Score Card */}
      <Card className={`border-2 ${getScoreBg(truth_score)}`}>
        <CardContent className="py-8 text-center">
          <p className="text-sm font-medium text-gray-600 uppercase tracking-wider">
            Truth Score
          </p>
          <p className={`mt-2 text-6xl font-bold ${getScoreColor(truth_score)}`}>
            {truth_score > 0 ? "+" : ""}
            {truth_score.toFixed(1)}%
          </p>
          <p className={`mt-1 text-lg font-medium ${getScoreColor(truth_score)}`}>
            {getScoreLabel(truth_score)}
          </p>
          <div className="mt-3">
            {getConfidenceBadge(report.confidence)}
            {report.cached && (
              <Badge variant="outline" className="ml-2">Cached</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Negotiation Lever */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Negotiation Lever</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 leading-relaxed">
            {report.negotiation_lever}
          </p>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-xs text-gray-500">Asking Price/m²</p>
            <p className="mt-1 text-xl font-bold">
              {formatEur(report.asking_price_per_m2)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-xs text-gray-500">GURS Avg/m²</p>
            <p className="mt-1 text-xl font-bold">
              {formatEur(report.avg_gurs_price_per_m2)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-xs text-gray-500">Comparables</p>
            <p className="mt-1 text-xl font-bold">{report.num_comps}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-xs text-gray-500">Size</p>
            <p className="mt-1 text-xl font-bold">{listing.size_m2} m²</p>
          </CardContent>
        </Card>
      </div>

      {/* Listing Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Listing Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div>
              <dt className="text-gray-500">Location</dt>
              <dd className="font-medium">
                {listing.neighborhood}, {listing.city}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Price</dt>
              <dd className="font-medium">{formatEur(listing.price_eur)} EUR</dd>
            </div>
            {listing.year_built && (
              <div>
                <dt className="text-gray-500">Year Built</dt>
                <dd className="font-medium">{listing.year_built}</dd>
              </div>
            )}
            {listing.floor != null && (
              <div>
                <dt className="text-gray-500">Floor</dt>
                <dd className="font-medium">{listing.floor}</dd>
              </div>
            )}
            {listing.description_summary && (
              <div className="col-span-2">
                <dt className="text-gray-500">Summary</dt>
                <dd className="font-medium">{listing.description_summary}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Price Trend */}
      {trend.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Price Trend — {listing.neighborhood}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TrendSparkline data={trend} />
          </CardContent>
        </Card>
      )}

      {/* Comparable Transactions */}
      {comps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Comparable Transactions ({comps.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Area</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">EUR/m²</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comps.map((comp, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-sm">
                      {comp.transaction_date}
                    </TableCell>
                    <TableCell className="text-sm">
                      {comp.neighborhood}
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {comp.size_m2} m²
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {formatEur(comp.price_eur)} EUR
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium">
                      {formatEur(comp.price_per_m2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {report.num_comps < 3 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="py-4 text-center text-sm text-yellow-800">
            Based on only {report.num_comps} transaction(s). Results may not be
            representative. Try expanding the search area or size range.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
