import { Button } from './components/Button';
import { UserType, ProductType } from './types';
import * as utils from './utils';

export function main(): void {
    console.log('Hello TypeScript');
}

export class App {
    private name: string;

    constructor(name: string) {
        this.name = name;
    }

    public run(): void {
        main();
    }
}

export default App;
