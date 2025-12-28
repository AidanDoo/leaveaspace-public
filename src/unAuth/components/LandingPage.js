import React from 'react';
import './LandingPage.css';
import NavBar from './NavBar.js';
import Timestamp from './Timestamp.js';

function LandingPage() {
  return (
    <div className="landing-page-container">
      <NavBar />
      <div className="description-container">
        <div className="description-inner">
          <h1 className="description-title">Formula 1 Grand Prix Race Timestamps</h1>
          <p className="description-text">Generates relevant timestamps for Formula 1 Grand Prix videos using OpenF1 API.</p>
          <p className="description-usage"><strong>How to Use:</strong><br />Select desired filters and enter the video timestamp for when the formation lap starts!</p>
        </div>
      </div>

      <Timestamp />
    </div>
  );
}
 
export default LandingPage;

