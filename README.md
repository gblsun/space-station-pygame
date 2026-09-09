# Projeto AP1 — Computação Gráfica e RA/RV
## Mundo Virtual Animado: Base Espacial e Campo de Asteroides

---

### Integrantes da Equipe
* [Fellipe Augusto - 2401525]
* [Gabriel Muchon - 2401895]
* [Paloma Eduarda - 2401660]
* [Victor Wenzel - 2401698]

---

### 1. Visão Geral do Projeto
Este projeto consiste na implementação de um ambiente virtual tridimensional animado e interativo desenvolvido inteiramente em **Python** com **Pygame**, sem a utilização de OpenGL, motores 3D comerciais ou bibliotecas externas de modelagem (atendendo à restrição didática do enunciado).

A aplicação renderiza uma cena espacial composta por uma base de lançamento com torre de suporte monolítica, um foguete aeroespacial composto, um corpo celeste esférico (Lua) e um cinturão de três asteroides instanciados com variação de parâmetros, além de um campo estelar dinâmico em profundidade. Toda a projeção tridimensional, sombreamento, oclusão, descarte de superfícies e traçado de raio foram calculados analiticamente através de matemática vetorial pura.

---

### 2. Instruções de Execução

#### Pré-requisitos
* **Python 3.10** ou superior instalado.
* Biblioteca **Pygame** instalada.

#### Instalação das Dependências
No terminal ou prompt de comando, execute:
```bash
pip install pygame
