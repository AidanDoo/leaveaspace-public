import React, { useEffect, useRef } from 'react';
import './Popup.css';

function Popup({ isOpen, onClose, title = 'Dialog', children }) {
	const dialogRef = useRef(null);

	// Basic focus management
	useEffect(() => {
		if (isOpen && dialogRef.current) {
			dialogRef.current.focus();
		}
	}, [isOpen]);

	if (!isOpen) return null;

	const handleOverlayClick = (e) => {
		if (e.target === e.currentTarget) onClose?.();
	};

	return (
		<div className="popup-overlay" onClick={handleOverlayClick}>
			<div
				className="popup-modal"
				role="dialog"
				aria-modal="true"
				aria-label={title}
				tabIndex={-1}
				ref={dialogRef}
			>
				<div className="popup-header">
					<h2 className="popup-title">{title}</h2>
					<button className="popup-close" onClick={onClose} aria-label="Close">
						×
					</button>
				</div>
				<div className="popup-content">{children}</div>
			</div>
		</div>
	);
}

export default Popup;

