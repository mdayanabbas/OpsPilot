'use client';

import { useState } from 'react';

export default function DashboardPage() {
  const [selectedRun, setSelectedRun] = useState<string | null>(null);

  // Dummy data
  const stats = [
    { label: 'Emails Processed', value: '1,234', color: 'bg-blue-500' },
    { label: 'Approved', value: '1,087', color: 'bg-green-500' },
    { label: 'Pending Review', value: '147', color: 'bg-orange-500' },
    { label: 'Success Rate', value: '88.1%', color: 'bg-purple-500' },
  ];

  const recentRuns = [
    {
      id: '1',
      email: 'customer@example.com',
      subject: 'App crashing on mobile',
      status: 'approved',
      timestamp: '2 hours ago',
    },
    {
      id: '2',
      email: 'user@domain.com',
      subject: 'Feature request: dark mode',
      status: 'pending',
      timestamp: '1 hour ago',
    },
    {
      id: '3',
      email: 'support@test.com',
      subject: 'Billing issue',
      status: 'approved',
      timestamp: '30 mins ago',
    },
    {
      id: '4',
      email: 'feedback@user.com',
      subject: 'Great product!',
      status: 'approved',
      timestamp: '15 mins ago',
    },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">OpsPilot Dashboard</h1>
          <p className="text-lg text-gray-600">AI-Powered Email Triage System</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6"
            >
              <div className={`${stat.color} w-12 h-12 rounded-lg mb-4`}></div>
              <p className="text-gray-600 text-sm font-medium">{stat.label}</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Recent Runs */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Recent Agent Runs</h2>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Email</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Subject</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Time</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Action</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr
                    key={run.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="py-4 px-4 text-gray-900">{run.email}</td>
                    <td className="py-4 px-4 text-gray-700">{run.subject}</td>
                    <td className="py-4 px-4">
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          run.status === 'approved'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-gray-600">{run.timestamp}</td>
                    <td className="py-4 px-4">
                      <button
                        onClick={() => setSelectedRun(run.id)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Run Details */}
        {selectedRun && (
          <div className="bg-white rounded-lg shadow-md p-6 mt-8 border-l-4 border-blue-500">
            <h3 className="text-xl font-bold text-gray-900 mb-4">
              Run Details: {selectedRun}
            </h3>
            <div className="space-y-4">
              <div className="bg-blue-50 p-4 rounded">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">AI Analysis:</span> Email classified as bug
                  report with high priority
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Suggested Response:</span> Thank you for
                  reporting. Our team is investigating this issue.
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedRun(null)}
              className="mt-4 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </main>
  );
}