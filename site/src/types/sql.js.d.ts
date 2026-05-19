declare module "sql.js" {
  interface SqlJsStatic {
    Database: new (data?: ArrayLike<number> | Buffer | null) => Database;
  }

  interface QueryExecResult {
    columns: string[];
    values: any[][];
  }

  interface Database {
    run(sql: string, params?: any[]): Database;
    exec(sql: string, params?: { bind?: any[] }): QueryExecResult[];
    export(): Uint8Array;
    close(): void;
  }

  interface InitOptions {
    locateFile?: (file: string) => string;
  }

  export default function initSqlJs(options?: InitOptions): Promise<SqlJsStatic>;
  export { SqlJsStatic, Database, QueryExecResult };
}
