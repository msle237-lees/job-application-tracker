import React, { useState, useEffect } from 'react';
import { getApplications, deleteApplication, getCompanies } from '../api';
import './ApplicationTable.css';

const ApplicationTable = ({ onEdit, onRefresh }) => {
  const [applications, setApplications] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, [onRefresh]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [appsResponse, companiesResponse] = await Promise.all([
        getApplications(),
        getCompanies()
      ]);
      setApplications(appsResponse.data);
      setCompanies(companiesResponse.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch applications: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this application?')) {
      return;
    }
    try {
      await deleteApplication(id);
      fetchData();
    } catch (err) {
      setError('Failed to delete application: ' + err.message);
    }
  };

  const getCompanyName = (companyId) => {
    const company = companies.find(c => c.company_id === companyId);
    return company ? company.name : companyId;
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const getStatusClass = (status) => {
    const statusClasses = {
      'new': 'status-new',
      'applied': 'status-applied',
      'recruiter': 'status-recruiter',
      'phone': 'status-phone',
      'technical': 'status-technical',
      'onsite': 'status-onsite',
      'offer': 'status-offer',
      'accepted': 'status-accepted',
      'rejected': 'status-rejected',
      'withdrawn': 'status-withdrawn',
    };
    return statusClasses[status] || 'status-default';
  };

  if (loading) return <div className="loading">Loading applications...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="application-table-container">
      <h2>Job Applications ({applications.length})</h2>
      {applications.length === 0 ? (
        <p className="empty-state">No applications yet. Click "Add Application" to get started!</p>
      ) : (
        <div className="table-wrapper">
          <table className="application-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Position</th>
                <th>Status</th>
                <th>Employment Type</th>
                <th>Salary Range</th>
                <th>Applied Date</th>
                <th>Last Update</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.application_id}>
                  <td className="company-cell">{getCompanyName(app.company_id)}</td>
                  <td className="position-cell">{app.position}</td>
                  <td>
                    <span className={`status-badge ${getStatusClass(app.status)}`}>
                      {app.status}
                    </span>
                  </td>
                  <td>{app.employment_type || '-'}</td>
                  <td>
                    {app.salary_min && app.salary_max
                      ? `${app.currency} ${app.salary_min.toLocaleString()} - ${app.salary_max.toLocaleString()}`
                      : '-'}
                  </td>
                  <td>{formatDate(app.applied_at)}</td>
                  <td>{formatDate(app.last_update)}</td>
                  <td className="actions-cell">
                    <button 
                      className="btn-edit"
                      onClick={() => onEdit(app)}
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button 
                      className="btn-delete"
                      onClick={() => handleDelete(app.application_id)}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ApplicationTable;
