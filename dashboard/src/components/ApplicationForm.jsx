import React, { useState, useEffect } from 'react';
import { createApplication, updateApplication, getCompanies, createCompany } from '../api';
import './ApplicationForm.css';

const STATUSES = ['new', 'applied', 'recruiter', 'phone', 'technical', 'onsite', 'offer', 'accepted', 'rejected', 'withdrawn'];

const ApplicationForm = ({ application, onSuccess, onCancel }) => {
  const [companies, setCompanies] = useState([]);
  const [showNewCompany, setShowNewCompany] = useState(false);
  const [formData, setFormData] = useState({
    company_id: '',
    position: '',
    status: 'new',
    employment_type: '',
    salary_min: '',
    salary_max: '',
    currency: 'USD',
    job_url: '',
    notes: ''
  });
  const [newCompany, setNewCompany] = useState({
    name: '',
    location: '',
    industry: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCompanies();
    if (application) {
      setFormData({
        company_id: application.company_id,
        position: application.position,
        status: application.status,
        employment_type: application.employment_type || '',
        salary_min: application.salary_min || '',
        salary_max: application.salary_max || '',
        currency: application.currency || 'USD',
        job_url: application.job_url || '',
        notes: application.notes || ''
      });
    }
  }, [application]);

  const fetchCompanies = async () => {
    try {
      const response = await getCompanies();
      setCompanies(response.data);
    } catch (err) {
      setError('Failed to fetch companies');
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleNewCompanyChange = (e) => {
    const { name, value } = e.target;
    setNewCompany(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAddCompany = async (e) => {
    e.preventDefault();
    if (!newCompany.name) {
      setError('Company name is required');
      return;
    }
    try {
      setLoading(true);
      const response = await createCompany(newCompany);
      setCompanies([...companies, response.data]);
      setFormData(prev => ({ ...prev, company_id: response.data.company_id }));
      setNewCompany({ name: '', location: '', industry: '' });
      setShowNewCompany(false);
      setError(null);
    } catch (err) {
      setError('Failed to create company: ' + err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.company_id || !formData.position) {
      setError('Company and position are required');
      return;
    }

    try {
      setLoading(true);
      const data = {
        ...formData,
        salary_min: formData.salary_min ? parseInt(formData.salary_min) : null,
        salary_max: formData.salary_max ? parseInt(formData.salary_max) : null,
      };

      if (application) {
        await updateApplication(application.application_id, data);
      } else {
        await createApplication(data);
      }
      
      onSuccess();
    } catch (err) {
      setError('Failed to save application: ' + err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="application-form-container">
      <h2>{application ? 'Edit Application' : 'Add New Application'}</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="application-form">
        <div className="form-group">
          <label htmlFor="company_id">Company *</label>
          <div className="company-select-wrapper">
            <select
              id="company_id"
              name="company_id"
              value={formData.company_id}
              onChange={handleChange}
              required
              disabled={showNewCompany}
            >
              <option value="">Select a company...</option>
              {companies.map(company => (
                <option key={company.company_id} value={company.company_id}>
                  {company.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-toggle-new-company"
              onClick={() => setShowNewCompany(!showNewCompany)}
            >
              {showNewCompany ? 'Cancel' : '+ New Company'}
            </button>
          </div>
        </div>

        {showNewCompany && (
          <div className="new-company-section">
            <h3>Add New Company</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="new-company-name">Company Name *</label>
                <input
                  id="new-company-name"
                  type="text"
                  name="name"
                  value={newCompany.name}
                  onChange={handleNewCompanyChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="new-company-location">Location</label>
                <input
                  id="new-company-location"
                  type="text"
                  name="location"
                  value={newCompany.location}
                  onChange={handleNewCompanyChange}
                />
              </div>
              <div className="form-group">
                <label htmlFor="new-company-industry">Industry</label>
                <input
                  id="new-company-industry"
                  type="text"
                  name="industry"
                  value={newCompany.industry}
                  onChange={handleNewCompanyChange}
                />
              </div>
            </div>
            <button
              type="button"
              className="btn-add-company"
              onClick={handleAddCompany}
              disabled={loading}
            >
              Add Company
            </button>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="position">Position *</label>
          <input
            id="position"
            type="text"
            name="position"
            value={formData.position}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="status">Status</label>
            <select
              id="status"
              name="status"
              value={formData.status}
              onChange={handleChange}
            >
              {STATUSES.map(status => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="employment_type">Employment Type</label>
            <input
              id="employment_type"
              type="text"
              name="employment_type"
              value={formData.employment_type}
              onChange={handleChange}
              placeholder="Full-time, Part-time, Contract..."
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="salary_min">Salary Min</label>
            <input
              id="salary_min"
              type="number"
              name="salary_min"
              value={formData.salary_min}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label htmlFor="salary_max">Salary Max</label>
            <input
              id="salary_max"
              type="number"
              name="salary_max"
              value={formData.salary_max}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label htmlFor="currency">Currency</label>
            <select
              id="currency"
              name="currency"
              value={formData.currency}
              onChange={handleChange}
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="CAD">CAD</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="job_url">Job URL</label>
          <input
            id="job_url"
            type="url"
            name="job_url"
            value={formData.job_url}
            onChange={handleChange}
            placeholder="https://..."
          />
        </div>

        <div className="form-group">
          <label htmlFor="notes">Notes</label>
          <textarea
            id="notes"
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            rows="4"
            placeholder="Any additional notes..."
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="btn-submit" disabled={loading}>
            {loading ? 'Saving...' : (application ? 'Update' : 'Create')}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ApplicationForm;
