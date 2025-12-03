import React, { useState } from 'react';
import type { FC } from 'react';

interface ButtonProps {
    label: string;
    onClick: () => void;
}

export const Button: FC<ButtonProps> = ({ label, onClick }) => {
    const [clicked, setClicked] = useState(false);

    const handleClick = () => {
        setClicked(true);
        onClick();
    };

    return <button onClick={handleClick}>{label}</button>;
};

export default Button;
