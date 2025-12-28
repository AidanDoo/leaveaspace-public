import React from 'react';
import './NavBar.css';
import leaveaspacelogo from '../../assets/leaveaspacelogo.png';

function NavBar() {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo-group">
          <img
            src={leaveaspacelogo}
            alt="Leave A Space Logo"
            className="navbar-logo-image"
          />
          <span className="navbar-title">Leave A Space</span>
        </div>
        <div className="navbar-subtitle">
          Powered by OpenF1.org · Built by Aidan Do
        </div>
      </div>
    </nav>
  );
}

export default NavBar;
