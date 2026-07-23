import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DonutChart, SparkAreaChart } from '@tremor/react';

const mockAllocation = [
  { name: 'Cash', value: 45000 },
  { name: 'TSLA', value: 25000 },
  { name: 'ETH', value: 30000 },
];

const mockVolatility = [
  { date: '2026-06-23', value: 0.12 },
  { date: '2026-06-28', value: 0.15 },
  { date: '2026-07-03', value: 0.22 },
  { date: '2026-07-08', value: 0.18 },
  { date: '2026-07-13', value: 0.14 },
  { date: '2026-07-18', value: 0.20 },
  { date: '2026-07-23', value: 0.17 },
];

export function Dashboard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-100 flex justify-between items-center">
            Portfolio Allocation
            <Badge variant="outline" className="text-slate-400 border-slate-700">Live</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 flex items-center justify-center">
            <DonutChart
              data={mockAllocation}
              category="value"
              index="name"
              colors={['#475569', '#94a3b8', '#e2e8f0']}
              className="h-full w-full"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-100 flex justify-between items-center">
            30-Day Volatility Risk
            <Badge className="bg-red-900/50 text-red-400 hover:bg-red-900/70 border-0">High Risk</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 flex flex-col justify-end pb-4">
            <div className="mb-4">
              <p className="text-sm text-slate-400">Current Standard Deviation</p>
              <p className="text-3xl font-bold text-slate-100">17.4%</p>
            </div>
            <SparkAreaChart
              data={mockVolatility}
              categories={['value']}
              index="date"
              colors={['#ef4444']}
              className="h-32 w-full"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
