/** Erros que o app sabe tratar: da API (formato único) e de rede. */
import type { RespostaErro } from './tipos';

/** Códigos do formato único da API (`{"erro": {"codigo", ...}}`). */
export type CodigoErroApi = 'nao_encontrado' | 'parametro_invalido' | 'banco_indisponivel' | 'erro_interno';
export type CodigoErroRede = 'sem_conexao' | 'timeout';

export class ErroApi extends Error {
  readonly status: number;
  readonly codigo: CodigoErroApi;

  constructor(status: number, codigo: CodigoErroApi, mensagem: string) {
    super(mensagem);
    this.name = 'ErroApi';
    this.status = status;
    this.codigo = codigo;
  }
}

export class ErroRede extends Error {
  readonly codigo: CodigoErroRede;

  constructor(codigo: CodigoErroRede) {
    super(codigo === 'timeout' ? 'Tempo de resposta esgotado' : 'Falha de conexão');
    this.name = 'ErroRede';
    this.codigo = codigo;
  }
}

const CODIGOS_API: readonly string[] = ['nao_encontrado', 'parametro_invalido', 'banco_indisponivel', 'erro_interno'];

function ehRespostaErro(corpo: unknown): corpo is RespostaErro {
  if (typeof corpo !== 'object' || corpo === null || !('erro' in corpo)) return false;
  const erro: unknown = corpo.erro;
  return typeof erro === 'object' && erro !== null && 'codigo' in erro && typeof erro.codigo === 'string';
}

/** Converte a resposta de erro da API (ou um corpo inesperado) em `ErroApi`. */
export function erroDaResposta(status: number, corpo: unknown): ErroApi {
  if (ehRespostaErro(corpo) && CODIGOS_API.includes(corpo.erro.codigo)) {
    return new ErroApi(status, corpo.erro.codigo as CodigoErroApi, corpo.erro.mensagem);
  }
  if (status === 404) return new ErroApi(status, 'nao_encontrado', 'Não encontrado');
  if (status === 422) return new ErroApi(status, 'parametro_invalido', 'Parâmetro inválido');
  if (status === 503) return new ErroApi(status, 'banco_indisponivel', 'Serviço indisponível');
  return new ErroApi(status, 'erro_interno', 'Erro inesperado');
}

/** Só vale a pena tentar de novo quando o problema pode ser passageiro. */
export function deveRepetir(erro: unknown): boolean {
  if (erro instanceof ErroRede) return true;
  return erro instanceof ErroApi && erro.codigo === 'banco_indisponivel';
}

export type CodigoErro = CodigoErroApi | CodigoErroRede | 'desconhecido';

export function codigoDoErro(erro: unknown): CodigoErro {
  if (erro instanceof ErroApi || erro instanceof ErroRede) return erro.codigo;
  return 'desconhecido';
}

const MENSAGENS: Record<CodigoErro, string> = {
  sem_conexao: 'Não foi possível falar com o servidor. Verifique sua conexão.',
  timeout: 'O servidor demorou demais para responder.',
  banco_indisponivel: 'O serviço está temporariamente indisponível.',
  nao_encontrado: 'Não encontramos esta oportunidade. Ela pode ter saído da base na última atualização.',
  parametro_invalido: 'Algum filtro ficou inválido. Tente limpar os filtros.',
  erro_interno: 'Algo deu errado no servidor.',
  desconhecido: 'Algo deu errado.',
};

export function mensagemDoErro(erro: unknown): string {
  return MENSAGENS[codigoDoErro(erro)];
}
