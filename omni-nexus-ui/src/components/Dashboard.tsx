import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DonutChart, SparkAreaChart } from '@tremor/react';

// FACT: Pass live data via props, stop using static arrays.
interface DashboardProps {
    allocationData: { name: string, value: number }[];
    volatilityData: { date: string, value: number }[];
    currentVolatility: number;
}

export function Dashboard({ allocationData, volatilityData, currentVolatility }: DashboardProps) {
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
              data={allocationData.length > 0 ? allocationData : [{ name: 'No Data', value: 1 }]}
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
            <Badge className={`${currentVolatility > 20 ? 'bg-red-900/50 text-red-400' : 'bg-emerald-900/50 text-emerald-400'} border-0`}>
                {currentVolatility > 20 ? 'High Risk' : 'Normal'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 flex flex-col justify-end pb-4">
            <div className="mb-4">
              <p className="text-sm text-slate-400">Current Standard Deviation</p>
              <p className="text-3xl font-bold text-slate-100">{currentVolatility.toFixed(2)}%</p>
            </div>
            <SparkAreaChart
              data={volatilityData}
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
