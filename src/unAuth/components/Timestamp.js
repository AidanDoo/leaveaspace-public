import React, { useState, useEffect } from 'react';
import './Timestamp.css';
import Popup from './Popup';
import { functions } from '../../firebase';
import { httpsCallable } from 'firebase/functions';

function Timestamp() {
  const [selectedYear, setSelectedYear] = useState(2025);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedGrandPrix, setSelectedGrandPrix] = useState('');
  const [selectedEventFilter, setSelectedEventFilter] = useState('all');
  const [driverFilter, setDriverFilter] = useState('');
  const [driverError, setDriverError] = useState('');
  const [timeInput, setTimeInput] = useState('');
  const [timeError, setTimeError] = useState('');
  const [generateError, setGenerateError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [timestampsPayload, setTimestampsPayload] = useState(null);
  const [formattedList, setFormattedList] = useState([]);
  
  const [availableCountries, setAvailableCountries] = useState([]);
  const [availableGrandPrix, setAvailableGrandPrix] = useState([]);
  const [allMeetings, setAllMeetings] = useState([]);
  const availableYears = [2023, 2024, 2025];
  const eventFilterOptions = ['All', 'Overtakes', 'Pits', 'Yellow and Red Flags'];
  const baseApiUrl = process.env.REACT_APP_BASE_API_URL;

  // Fetch races data from OpenF1 API when year changes
  useEffect(() => {
    const fetchRaces = async () => {
      try {
        setLoading(true);
        const url = `${baseApiUrl}meetings?year=${selectedYear}`;
        // console.log('Fetching from:', url);
        
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        // console.log('API Response:', data);

        setAllMeetings(data);

        // Extract unique countries
        const countriesSet = new Set();
        data.forEach(meeting => {
          if (meeting.country_name) countriesSet.add(meeting.country_name);
        });

        const sortedCountries = Array.from(countriesSet).sort();
        setAvailableCountries(sortedCountries);

        // Set default country to first option
        if (sortedCountries.length > 0) setSelectedCountry(sortedCountries[0]);
      } catch (error) {
        console.error('Error fetching races:', error);
        setAvailableCountries([]);
        setAvailableGrandPrix([]);
        setAllMeetings([]);
      } finally {
        setLoading(false);
      }
    };

    if (baseApiUrl) fetchRaces();
  }, [selectedYear, baseApiUrl]);

  // Filter Grand Prix when country changes
  useEffect(() => {
    if (selectedCountry && allMeetings.length > 0) {
      const filteredMeetings = allMeetings.filter(meeting => meeting.country_name === selectedCountry);
      const sortedRaces = filteredMeetings.map(meeting => meeting.meeting_name).sort();

      setAvailableGrandPrix(sortedRaces);
      if (sortedRaces.length > 0) setSelectedGrandPrix(sortedRaces[0]);
    }
  }, [selectedCountry, allMeetings]);

  const handleYearChange = e => {
    setSelectedYear(parseInt(e.target.value));
  };

  const handleCountryChange = e => {
    setSelectedCountry(e.target.value);
  };

  const handleGrandPrixChange = e => {
    setSelectedGrandPrix(e.target.value);
  };

  const handleEventFilterChange = e => {
    setSelectedEventFilter(e.target.value);
  };

  const validateDriverNumber = value => {
    // allow empty = "all drivers"
    if (value.trim() === '') return true;
  
    const driverRegex = /^([1-9][0-9]?)$/;
    return driverRegex.test(value.trim());
  };
  

  const handleDriverFilterChange = e => {
    const value = e.target.value;
    setDriverFilter(value);
  
    if (value === '') {
      setDriverError('');
      // Handle case where both fields are valid
      if (!timeError) setGenerateError('');
      return;
    }
  
    if (!validateDriverNumber(value)) {
      setDriverError('Driver number must be a single number between 1 and 99');
    } else {
      // Handle case where both fields are valid
      if (!timeError) setGenerateError('');
      setDriverError('');
    }
  };

  const validateTimeFormat = time => {
    // HH:MM:SS format validation
    const timeRegex = /^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$/;
    return timeRegex.test(time);
  };

  const handleTimeChange = e => {
    const value = e.target.value;
    setTimeInput(value);
    
    if (value === '') {
      setTimeError('');
      if (!driverError) setGenerateError('');
      return;
    }
    
    if (!validateTimeFormat(value)) {
      setTimeError('Please enter time in HH:MM:SS format');
    } else {
      if (!driverError) setGenerateError('');
      setTimeError('');
    }
  };

  const handleGenerateTimestamps = async () => {
    if (driverError || timeError) {
      setGenerateError('Invalid field(s)');
      return;
    }
    
    if (!selectedYear || !selectedCountry || !selectedGrandPrix) {
      setGenerateError('Please select year, country, and Grand Prix');
      return;
    }

    setGenerateError('');
    setLoading(true);

    try {
      // Call Firebase Cloud Function
      const generateTimestamps = httpsCallable(functions, 'generate_timestamps');
      const result = await generateTimestamps({
        year: selectedYear,
        country: selectedCountry,
        meeting_name: selectedGrandPrix,
        driver_number: driverFilter ? parseInt(driverFilter) : null,
        event_filter: selectedEventFilter.toLowerCase(),
        calibration_offset: timeInput || null
      });

      // console.log('[Timestamp] Received data from generate_timestamps:', result.data);
      // console.log('[Timestamp] User inputs:', {
        // year: selectedYear,
        // country: selectedCountry,
        // grandPrix: selectedGrandPrix,
        // eventFilter: selectedEventFilter,
        // driverFilter: driverFilter || 'all',
        // startTime: timeInput || '00:00:00',
        // timestampData: result.data
      // });
      // If Cloud Function returns the formatted list directly
      if (Array.isArray(result.data)) {
        setFormattedList(result.data);
      } else if (result?.data?.data && Array.isArray(result.data.data)) {
        // Fallback in case the function still wraps in an object
        setFormattedList(result.data.data);
      } else {
        setFormattedList([]);
      }
      setTimestampsPayload(result.data);
      setIsPopupOpen(true);
    } catch (error) {
      console.error('[Timestamp] Error calling generate_timestamps:', error);
      setGenerateError('Failed to generate timestamps');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="timestamp-container">
      <div className="timestamp-grid">
        <div className="timestamp-field">
          <label className="timestamp-label">Select Year</label>
          <select 
            className="timestamp-select" 
            value={selectedYear}
            onChange={handleYearChange}
          >
            {availableYears.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>

        <div className="timestamp-field">
          <label className="timestamp-label">Select Grand Prix</label>
          <select 
            className="timestamp-select" 
            value={selectedGrandPrix}
            onChange={handleGrandPrixChange}
          >
            {availableGrandPrix.map(gp => (
              <option key={gp} value={gp}>{gp}</option>
            ))}
          </select>
        </div>

        <div className="timestamp-field">
          <label className="timestamp-label">Select Country</label>
          <select 
            className="timestamp-select" 
            value={selectedCountry}
            onChange={handleCountryChange}
          >
            {availableCountries.map(country => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
        </div>

        <div className="timestamp-field">
          <label className="timestamp-label">Filter by event</label>
          <select 
            className="timestamp-select" 
            value={selectedEventFilter}
            onChange={handleEventFilterChange}
          >
            {eventFilterOptions.map(event => (
              <option key={event} value={event}>{event}</option>
            ))}
          </select>
        </div>

        <div className="timestamp-field">
          <label className="timestamp-label">Filter by driver numbers</label>
          <input
            type="text"
            className={`timestamp-input ${driverError ? 'timestamp-input-error' : ''}`}
            value={driverFilter}
            onChange={handleDriverFilterChange}
            placeholder="Leave empty to filter by all drivers"
          />
          {driverError && <span className="timestamp-error">{driverError}</span>}
        </div>

        <div className="timestamp-field">
          <label className="timestamp-label">Enter Formation Lap Start Time (HH:MM:SS)</label>
          <input
            type="text"
            className={`timestamp-input ${timeError ? 'timestamp-input-error' : ''}`}
            value={timeInput}
            onChange={handleTimeChange}
            placeholder="Leave empty to use start time 00:00:00"
            maxLength={8}
          />
          {timeError && <span className="timestamp-error">{timeError}</span>}
        </div>

        <div className="timestamp-field timestamp-button-field">
          <button
            type="button"
            className="timestamp-button"
            onClick={handleGenerateTimestamps}
            disabled={loading}
          >
            {loading ? 'Generating...' : 'Generate Timestamps'}
          </button>
          {generateError && <span className="timestamp-error">{generateError}</span>}
        </div>
      </div>
      <Popup
        isOpen={isPopupOpen}
        title="Timestamps"
        onClose={() => setIsPopupOpen(false)}
      >
        {formattedList && formattedList.length > 0 ? (
          <ul>
            {formattedList.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        ) : timestampsPayload ? (
          <pre className="popup-pre">{JSON.stringify(timestampsPayload, null, 2)}</pre>
        ) : (
          <div>No data returned.</div>
        )}
      </Popup>
    </div>
  );
}

export default Timestamp;

