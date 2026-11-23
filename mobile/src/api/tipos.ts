/** Apelidos legíveis para os tipos gerados do OpenAPI (schema.d.ts). */
import type { components } from './schema';

type Esquemas = components['schemas'];

export type OportunidadeItem = Esquemas['OportunidadeItem'];
export type PaginaOportunidades = Esquemas['PaginaOportunidades'];
export type DetalheOportunidade = Esquemas['DetalheOportunidade'];
export type Oportunidade = Esquemas['Oportunidade'];
export type Rota = Esquemas['Rota'];
export type ContextoMunicipal = Esquemas['ContextoMunicipal'];
export type Meta = Esquemas['Meta'];
export type Fonte = Esquemas['Fonte'];
export type Quantidade = Esquemas['Quantidade'];
export type Operacao = Esquemas['Operacao'];
export type Municipio = Esquemas['Municipio'];
export type ResiduoBusca = Esquemas['ResiduoBusca'];
export type RespostaErro = Esquemas['RespostaErro'];
export type Ordem = NonNullable<
  NonNullable<
    import('./schema').operations['listar_oportunidades_v1_oportunidades_get']['parameters']['query']
  >['ordem']
>;
