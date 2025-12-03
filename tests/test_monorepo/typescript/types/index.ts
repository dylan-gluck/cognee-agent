export interface UserType {
    id: string;
    name: string;
    email: string;
}

export interface ProductType {
    id: string;
    title: string;
    price: number;
}

export type ID = string | number;

export enum Status {
    Active = 'active',
    Inactive = 'inactive',
    Pending = 'pending'
}

export type Callback<T> = (data: T) => void;
