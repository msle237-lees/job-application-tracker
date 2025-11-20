import React, { useState, useEffect } from 'react';
import { getAnalytics } from '../api';
import './Analytics.css';

const Analytics = ({ onRefresh }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, [onRefresh]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await getAnalytics();
      setAnalytics(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading analytics...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!analytics) return null;

  const statusOrder = ['new', 'applied', 'recruiter', 'phone', 'technical', 'onsite', 'offer', 'accepted', 'rejected', 'withdrawn'];
  const sortedStatuses = Object.entries(analytics.status_breakdown)
    .sort(([a], [b]) => statusOrder.indexOf(a) - statusOrder.indexOf(b));

  const totalApps = analytics.total_applications;
  const maxCount = Math.max(...Object.values(analytics.status_breakdown), 1);

  return (
    <div className="analytics-container">
      <h2>Analytics Dashboard</h2>
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{analytics.total_applications}</div>
          <div className="stat-label">Total Applications</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-value">{analytics.total_companies}</div>
          <div className="stat-label">Companies</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-value">{analytics.recent_activity}</div>
          <div className="stat-label">Active (Last 7 Days)</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-value">
            {totalApps > 0 
              ? Math.round((analytics.status_breakdown.offer || 0) / totalApps * 100) 
              : 0}%
          </div>
          <div className="stat-label">Offer Rate</div>
        </div>
      </div>

      <div className="status-breakdown">
        <h3>Status Breakdown</h3>
        <div className="status-chart">
          {sortedStatuses.map(([status, count]) => {
            const percentage = totalApps > 0 ? (count / totalApps * 100).toFixed(1) : 0;
            const barWidth = totalApps > 0 ? (count / maxCount * 100) : 0;
            
            return (
              <div key={status} className="status-row">
                <div className="status-name">{status}</div>
                <div className="status-bar-container">
                  <div 
                    className={`status-bar status-${status}`}
                    style={{ width: `${barWidth}%` }}
                  >
                    <span className="status-count">{count}</span>
                  </div>
                </div>
                <div className="status-percentage">{percentage}%</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Analytics;
