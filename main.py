import io
import re
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sympy import (
    symbols, solve, solve_univariate_inequality, Symbol,
    diff, integrate, limit, oo, Matrix, lambdify, Eq, latex,
    factor, expand, simplify, Sum, Product, N
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BOT_TOKEN = "8905569753:AAGnGsd6GVrQucX_5tX9uBA__m_iBjH5Mjw"

TRANSFORMATIONS = (standard_transformations + (implicit_multiplication_application,))

def parse_math(expr_str: str):
    """Matematik ifodalarni 2x -> 2*x ko'rinishida xatosiz parse qilish."""
    clean = expr_str.strip().replace("^", "**").replace("÷", "/").replace(":", "/")
    return parse_expr(clean, transformations=TRANSFORMATIONS)

def safe_str(val) -> str:
    """SymPy obyektlarini matnga xavfsiz o'tkazuvchi drayver."""
    try:
        if hasattr(val, 'free_symbols') and val.free_symbols:
            return str(val)
        f_val = float(val.evalf() if hasattr(val, 'evalf') else val)
        return f"{f_val:.4f}".rstrip('0').rstrip('.')
    except Exception:
        return str(val)

# ==============================================================================
# 1. CHUQURLASHTIRILGAN MATEMATIKA DVIGATELI (STEP-BY-STEP YECHIMLAR)
# ==============================================================================
class AdvancedMathEngine:
    def __init__(self):
        self.x = Symbol('x')
        self.y = Symbol('y')
        self.z = Symbol('z')

    def render_latex_to_image(self, latex_str: str, title: str = "Matematik Yechim") -> io.BytesIO:
        """Matematik formulani yuqori sifatli PNG kartochkaga aylantirish."""
        fig, ax = plt.subplots(figsize=(8, 3), dpi=200)
        ax.axis('off')
        ax.text(0.5, 0.8, title, fontsize=12, fontweight='bold', ha='center', va='center', color='#1A365D')
        ax.text(0.5, 0.4, f"${latex_str}$", fontsize=14, ha='center', va='center', color='#2B6CB0')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.3, facecolor='#F7FAFC')
        buf.seek(0)
        plt.close(fig)
        return buf

    def generate_function_graph(self, expr_str: str) -> io.BytesIO:
        """Ox va Oy koordinatalar o'qi hamda to'ri ko'rsatilgan grafik chizish."""
        expr = parse_math(expr_str)
        x_vals = np.linspace(-10, 10, 600)
        f = lambdify(self.x, expr, modules=["numpy", "math"])
        
        try:
            y_vals = f(x_vals)
        except Exception:
            y_vals = [float(expr.subs(self.x, val)) for val in x_vals]

        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
        ax.plot(x_vals, y_vals, label=f"y = {expr_str}", color="#2B6CB0", linewidth=2.5)
        
        # OX va OY o'qlarini chizish
        ax.axhline(0, color='red', linewidth=1.5, linestyle='-', label="Ox o'qi")
        ax.axvline(0, color='green', linewidth=1.5, linestyle='-', label="Oy o'qi")
        
        # Koordinatalar boshi (0,0)
        ax.plot(0, 0, 'ko', markersize=6)
        ax.text(0.3, 0.3, 'O(0,0)', fontsize=10, fontweight='bold')

        ax.grid(True, which='both', linestyle=':', alpha=0.7)
        ax.set_title(f"Funksiya Grafigi: y = {expr_str}", fontsize=13, fontweight='bold', pad=12)
        ax.set_xlabel("Ox (Abssissa o'qi)", fontsize=11, fontweight='bold')
        ax.set_ylabel("Oy (Ordinata o'qi)", fontsize=11, fontweight='bold')
        ax.legend(loc="best")

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def process_query(self, query: str):
        raw_text = query.strip()

        # 1. FUNKSIYA GRAFIGI
        if raw_text.lower().startswith("grafik:"):
            expr_str = raw_text.split(":", 1)[1].strip()
            buf = self.generate_function_graph(expr_str)
            return "graph", buf, f"y = {expr_str}"

        # 2. HOSILA OLISH (BOSQICHMA-BOSQICH)
        if raw_text.lower().startswith(("hosila:", "diff:")):
            expr_str = raw_text.split(":", 1)[1].strip()
            expr = parse_math(expr_str)
            res = diff(expr, self.x)
            
            steps = (
                f"📐 **HOSILA OLISH BOSQICHLARI:**\n\n"
                f"1️⃣ **Dastlabki funksiya:** `f(x) = {expr_str}`\n"
                f"2️⃣ **Differensiallash qoidasi qo'llanildi:** `d/dx [{expr}]`\n"
                f"3️⃣ **Yechim (Hosilasi):** `f'(x) = {res}`"
            )
            img_buf = self.render_latex_to_image(f"f'(x) = {latex(res)}", title=f"f(x) = {expr_str} hosilasi")
            return "both", (steps, img_buf), None

        # 3. INTEGRAL HISOBLASH (BOSQICHMA-BOSQICH)
        if raw_text.lower().startswith(("integral:", "int:")):
            body = raw_text.split(":", 1)[1].strip()
            if "," in body:
                parts = [p.strip() for p in body.split(",")]
                expr = parse_math(parts[0])
                a = parse_math(parts[1])
                b = parse_math(parts[2])
                
                antiderivative = integrate(expr, self.x)
                res = integrate(expr, (self.x, a, b))
                eval_val = safe_str(res)
                
                steps = (
                    f"∫ **ANIQLANGAN INTEGRAL YECHIMI:**\n\n"
                    f"1️⃣ **Integrallanuvchi funksiya:** `f(x) = {parts[0]}`\n"
                    f"2️⃣ **Boshlang'ich funksiya F(x):** `{antiderivative}`\n"
                    f"3️⃣ **Nyu-ton-Leybnits formulasi:** `F({b}) - F({a})`\n"
                    f"4️⃣ **Aniq qiymat:** `{res}` (≈ `{eval_val}`)"
                )
                img_buf = self.render_latex_to_image(f"\\int_{{{latex(a)}}}^{{{latex(b)}}} ({latex(expr)}) dx = {latex(res)}", title="Aniqlangan Integral")
            else:
                expr = parse_math(body)
                res = integrate(expr, self.x)
                steps = (
                    f"∫ **CHEKSIZ INTEGRAL YECHIMI:**\n\n"
                    f"1️⃣ **Integrallanuvchi funksiya:** `f(x) = {body}`\n"
                    f"2️⃣ **Integrallash jarayoni:** `∫ ({expr}) dx`\n"
                    f"3️⃣ **Natija:** `{res} + C`"
                )
                img_buf = self.render_latex_to_image(f"\\int ({latex(expr)}) dx = {latex(res)} + C", title="Cheksiz Integral")
            return "both", (steps, img_buf), None

        # 4. LIMIT HISOBLASH (BOSQICHMA-BOSQICH)
        if raw_text.lower().startswith("limit:"):
            body = raw_text.split(":", 1)[1].strip()
            parts = [p.strip() for p in body.split(",")] if "," in body else [body, "0"]
            expr = parse_math(parts[0])
            target_str = parts[1].replace("x->", "").strip()
            target = oo if target_str in ["oo", "inf", "cheksizlik"] else parse_math(target_str)
            
            res = limit(expr, self.x, target)
            steps = (
                f"🎯 **LIMIT YECHISH BOSQICHLARI:**\n\n"
                f"1️⃣ **Limit ifodasi:** `lim (x → {target}) [{expr}]`\n"
                f"2️⃣ **X o'rniga intilayotgan qiymat qo'yildi**\n"
                f"3️⃣ **Natija:** `{res}`"
            )
            img_buf = self.render_latex_to_image(f"\\lim_{{x \\to {latex(target)}}} \\left({latex(expr)}\\right) = {latex(res)}", title="Limit Natijasi")
            return "both", (steps, img_buf), None

        # 5. MATRITSA VA DETERMINANT
        if raw_text.lower().startswith("matritsa:"):
            matrix_str = raw_text.split(":", 1)[1].strip()
            M = Matrix(parse_math(matrix_str))
            det_M = M.det()
            inv_M = M.inv() if det_M != 0 else "Teskari matritsa mavjud emas (det=0)"
            
            steps = (
                f"🔢 **MATRITSA BOSQICHMA-BOSQICH TAHLILI:**\n\n"
                f"1️⃣ **Berilgan Matritsa A:**\n`{M}`\n\n"
                f"2️⃣ **Determinant |A| hisoblandi:** `{det_M}`\n"
                f"3️⃣ **Teskari matritsa A⁻¹:**\n`{inv_M}`"
            )
            img_buf = self.render_latex_to_image(f"A = {latex(M)}, \\quad \\det(A) = {latex(det_M)}", title="Matritsa Tahlili")
            return "both", (steps, img_buf), None

        # 6. PROGRESSIYA VA YIG'INDI (SERIES)
        if raw_text.lower().startswith("yigindi:"):
            body = raw_text.split(":", 1)[1].strip()
            parts = [p.strip() for p in body.split(",")]
            expr = parse_math(parts[0])
            n_start = int(parts[1])
            n_end = int(parts[2])
            n = Symbol('n')
            
            s_val = Sum(expr, (n, n_start, n_end)).doit()
            steps = (
                f"📊 **YIG'INDI HISOBLASH (∑):**\n\n"
                f"1️⃣ **Umumiy had formulasi:** `{expr}`\n"
                f"2️⃣ **Chegaralar:** n = {n_start} dan n = {n_end} gacha\n"
                f"3️⃣ **Umumiy Yig'indi:** `{s_val}`"
            )
            img_buf = self.render_latex_to_image(f"\\sum_{{n={n_start}}}^{{{n_end}}} ({latex(expr)}) = {latex(s_val)}", title="Yig'indi Natijasi")
            return "both", (steps, img_buf), None

        # 7. TENGLAMALAR VA TENGLAMALAR TIZIMI
        clean_input = raw_text.replace("^", "**")
        if "=" in clean_input:
            parts = clean_input.split("=")
            lhs = parse_math(parts[0])
            rhs = parse_math(parts[1])
            eq = Eq(lhs, rhs)
            sol = solve(eq, self.x)
            
            steps = (
                f"⚡ **TENGLAMANI BOSQICHMA-BOSQICH YECHISH:**\n\n"
                f"1️⃣ **Dastlabki tenglama:** `{clean_input}`\n"
                f"2️⃣ **Standart ko'rinishga keltirildi:** `{lhs - rhs} = 0`\n"
                f"3️⃣ **Ildizlar (Yechim):** `x = {sol}`"
            )
            img_buf = self.render_latex_to_image(f"x = {latex(sol)}", title=f"Tenglama Yechimi")
            return "both", (steps, img_buf), None

        # 8. ALGEBRAIK SODDALASHTIRISH VA KO'PAYTUVCHILARGA AJRATISH
        expr = parse_math(clean_input)
        factored = factor(expr)
        expanded = expand(expr)
        eval_val = safe_str(expr)
        
        steps = (
            f"🧮 **ALGEBRAIK IFODA TAHLILI:**\n\n"
            f"• **Dastlabki:** `{clean_input}`\n"
            f"• **Soddalashgani:** `{expr}`\n"
            f"• **Ko'paytuvchilarga ajralgani:** `{factored}`\n"
            f"• **Qavslar ochilgani:** `{expanded}`\n"
            f"• **Sonli qiymati:** `{eval_val}`"
        )
        img_buf = self.render_latex_to_image(f"{latex(expr)} = {latex(factored)}", title="Algebraik Soddalashtirish")
        return "both", (steps, img_buf), None

# ==============================================================================
# 2. CHUQURLASHTIRILGAN KIMYO DVIGATELI (KINETIKA, ORGANIKA, STEXIOMETRIYA)
# ==============================================================================
class ChemistryEngine:
    ATOMIC_MASSES = {
        'H': 1.008, 'He': 4.0026, 'Li': 6.94, 'Be': 9.0122, 'B': 10.81,
        'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998, 'Na': 22.990,
        'Mg': 24.305, 'Al': 26.982, 'Si': 28.085, 'P': 30.974, 'S': 32.06,
        'Cl': 35.45, 'K': 39.098, 'Ca': 40.078, 'Fe': 55.845, 'Cu': 63.546,
        'Zn': 65.38, 'Ag': 107.87, 'I': 126.90, 'Ba': 137.33, 'Au': 196.97
    }

    def parse_formula(self, formula: str):
        pattern = r'([A-Z][a-z]*)(\d*)'
        matches = re.findall(pattern, formula)
        element_counts = {}
        for elem, count in matches:
            if not elem: continue
            c = int(count) if count else 1
            element_counts[elem] = element_counts.get(elem, 0) + c
        return element_counts

    def calculate_molar_mass(self, formula: str):
        counts = self.parse_formula(formula)
        if not counts:
            return "❌ Kimyoviy formula xato kiritildi!"

        total_mass = 0.0
        details = []
        for elem, count in counts.items():
            if elem in self.ATOMIC_MASSES:
                m = float(self.ATOMIC_MASSES[elem]) * count
                total_mass += m
                details.append(f"• **{elem}**: {count} ta × {self.ATOMIC_MASSES[elem]} = `{m:.2f} g/mol`")
            else:
                return f"❌ Noma'lum element: `{elem}`"

        res_str = (
            f"🧪 **KIMYOVIY MODDA TAHLILI ({formula}):**\n\n"
            f"• **Molyar Massa (M):** `{total_mass:.2f} g/mol`\n\n"
            f"**Elementlar ulushi va hisob-kitob:**\n" + "\n".join(details)
        )
        return res_str

    def process_kinetics(self, c1: float, c2: float, time_sec: float):
        """Kimyoviy reaksiya tezligini hisoblash (v = ΔC / Δt)."""
        delta_c = abs(c1 - c2)
        v = delta_c / time_sec
        return (
            f"⚡ **KIMYOVIY REAKSIYA TEZLIGI (KINETIKA):**\n\n"
            f"• **Dastlabki konsentratsiya (C₁):** `{c1} mol/l`\n"
            f"• **Oxirgi konsentratsiya (C₂):** `{c2} mol/l`\n"
            f"• **Vaqt oralig'i (Δt):** `{time_sec} sekund`\n"
            f"• **Konsentratsiya o'zgarishi (ΔC):** `{delta_c:.4f} mol/l`\n\n"
            f"🎯 **Reaksiya tezligi (v = ΔC/Δt):** `{v:.6f} mol/(l·s)`"
        )

    def process_organics(self, compound_type: str, n_atoms: int):
        """Organik birikmalar (Alkan, Alken, Alkin) tahlili va yonish reaksiyasi."""
        ctype = compound_type.lower().strip()
        if ctype in ["alkan", "alkane"]:
            c = n_atoms
            h = 2 * n_atoms + 2
            molar = c * 12.011 + h * 1.008
            o2_moles = (3 * c + 1) / 2
            co2_moles = c
            h2o_moles = c + 1
            formula = f"C{c}H{h}"
            res = (
                f"🧬 **ORGANIK KIMYO (ALKANLAR TAHLILI):**\n\n"
                f"• **Gomolagik formula:** CₙH₂ₙ₊₂ (n={n_atoms})\n"
                f"• **Brutto formula:** `{formula}`\n"
                f"• **Molyar massa:** `{molar:.2f} g/mol`\n\n"
                f"🔥 **Yonish reaksiyasi tenglamasi:**\n"
                f"`{formula} + {o2_moles}O₂ → {co2_moles}CO₂ + {h2o_moles}H₂O`"
            )
            return res
        elif ctype in ["alken", "alkene"]:
            c = n_atoms
            h = 2 * n_atoms
            molar = c * 12.011 + h * 1.008
            formula = f"C{c}H{h}"
            res = (
                f"🧬 **ORGANIK KIMYO (ALKENLAR TAHLILI):**\n\n"
                f"• **Gomolagik formula:** CₙH₂ₙ (n={n_atoms})\n"
                f"• **Brutto formula:** `{formula}`\n"
                f"• **Molyar massa:** `{molar:.2f} g/mol`\n"
                f"• **Tarkibida 1 ta qo'sh bog' (C=C) bor.**"
            )
            return res
        elif ctype in ["alkin", "alkyne"]:
            c = n_atoms
            h = 2 * n_atoms - 2
            molar = c * 12.011 + h * 1.008
            formula = f"C{c}H{h}"
            res = (
                f"🧬 **ORGANIK KIMYO (ALKINLAR TAHLILI):**\n\n"
                f"• **Gomolagik formula:** CₙH₂ₙ₋₂ (n={n_atoms})\n"
                f"• **Brutto formula:** `{formula}`\n"
                f"• **Molyar massa:** `{molar:.2f} g/mol`\n"
                f"• **Tarkibida 1 ta uch bog' (C≡C) bor.**"
            )
            return res
        else:
            return "❌ Noma'lum organik birikma sinfi! (Faqat: alkan, alken, alkin)"

# ==============================================================================
# 3. CHUQURLASHTIRILGAN BIOLOGIYA DVIGATELI (ATF, FOTOSINTEZ, DNK, GENETIKA)
# ==============================================================================
class BiologyEngine:
    def process_atf(self, mol_glucose: float):
        """Energiya almashinuvi va ATF hosil bo'lish bosqichlari."""
        chala_atf = mol_glucose * 2
        to_liq_atf = mol_glucose * 38
        energiya_kj = mol_glucose * 2800

        res_str = (
            f"🧬 **ENERGIYA ALMASHINUVI (BIOLOGIYA MASALASI):**\n\n"
            f"• **Parchalangan glyukoza:** `{mol_glucose} mol`\n"
            f"1️⃣ **Glikoliz (Chala parchalanish):** `{chala_atf:.0f} mol ATF` + 2 mol sut kislotasi\n"
            f"2️⃣ **Aerob bosqich (To'liq parchalanish):** `{to_liq_atf - chala_atf:.0f} mol ATF`\n"
            f"3️⃣ **Jami ATF chiqqani:** `{to_liq_atf:.0f} mol ATF`\n\n"
            f"📊 **Energiya balansi:**\n"
            f"• **Jami ajralgan energiya:** `{energiya_kj:.1f} kJ`\n"
            f"• **Issiqlik bo'lib yo'qolgani (45%):** `{energiya_kj * 0.45:.1f} kJ`\n"
            f"• **ATF bog'larida jamlangani (55%):** `{energiya_kj * 0.55:.1f} kJ`"
        )
        return res_str

    def process_photosynthesis(self, glucose_grams: float):
        """Fotosintez jarayoni hisob-kitoblari."""
        mol_glucose = glucose_grams / 180.16
        co2_moles = mol_glucose * 6
        o2_moles = mol_glucose * 6
        co2_liters = co2_moles * 22.4
        o2_liters = o2_moles * 22.4

        return (
            f"🌿 **FOTOSINTEZ JARAYONI MASALASI:**\n\n"
            f"• **Hosil bo'lgan glyukoza:** `{glucose_grams} gramm` (`{mol_glucose:.3f} mol`)\n"
            f"• **Reaksiya:** `6CO₂ + 6H₂O + Quyosh energiyasi → C₆H₁₂O₆ + 6O₂`\n\n"
            f"🎯 **Sarflangan va ajralgan moddalar:**\n"
            f"• **Yutilgan CO₂ hajmi:** `{co2_liters:.2f} litr` (`{co2_moles:.2f} mol`)\n"
            f"• **Ajralgan O₂ hajmi:** `{o2_liters:.2f} litr` (`{o2_moles:.2f} mol`)\n"
            f"• **Sarflangan H₂O miqdori:** `{mol_glucose * 6 * 18:.2f} gramm`"
        )

    def process_dna(self, dna_seq: str):
        """DNK, i-RNK, vodorod bog'lar va molekulyar massa tahlili."""
        seq = dna_seq.upper().replace(" ", "")
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        rna_map = {'A': 'U', 'T': 'A', 'G': 'C', 'C': 'G'}

        comp_dna = "".join([complement.get(n, '?') for n in seq])
        i_rna = "".join([rna_map.get(n, '?') for n in seq])

        counts = {n: seq.count(n) for n in ['A', 'T', 'G', 'C']}
        h_bonds = (counts['A'] + counts['T']) * 2 + (counts['G'] + counts['C']) * 3
        dna_len_nm = len(seq) * 0.34
        dna_mass = len(seq) * 2 * 345  # Har bir nukleotid o'rtacha 345 g/mol

        res_str = (
            f"🔬 **DNK / RNK MOLEKULYAR BIOLOGIYA TAHLILI:**\n\n"
            f"• **I-Zanjir DNK:** `{seq}`\n"
            f"• **II-Zanjir (Komplementar):** `{comp_dna}`\n"
            f"• **Sintezlangan i-RNK:** `{i_rna}`\n\n"
            f"📊 **Parametrlar:**\n"
            f"• **Nukleotidlar:** A={counts['A']}, T={counts['T']}, G={counts['G']}, C={counts['C']}\n"
            f"• **Vodorod bog'lari soni:** `{h_bonds} ta`\n"
            f"• **DNK fragmenti uzunligi:** `{dna_len_nm:.2f} nm`\n"
            f"• **DNK molekulyar massasi:** `{dna_mass} g/mol`"
        )
        return res_str

    def process_genetics_monohybrid(self, p_genotype: str):
        """Genetika: Monogibrid chatishtirish (Masalan: Aa x Aa)."""
        clean = p_genotype.replace(" ", "").upper()
        if "X" in clean:
            parents = clean.split("X")
        else:
            parents = [clean[:2], clean[2:]] if len(clean) == 4 else ["AA", "AA"]

        p1, p2 = parents[0], parents[1]
        
        # Gametalar
        g1 = list(set(p1))
        g2 = list(set(p2))
        
        offspring = []
        for a1 in p1:
            for a2 in p2:
                gen = "".join(sorted([a1, a2]))
                offspring.append(gen)

        total = len(offspring)
        gen_counts = {g: offspring.count(g) for g in set(offspring)}
        
        res = f"🧬 **GENETIKA MASALASI (MONOGIBRID CHATISHTIRISH):**\n\n"
        res += f"• **Ota-ona genotipi (P):** `{p1}  ×  {p2}`\n"
        res += f"• **Gametalar:** `{g1}` va `{g2}`\n\n"
        res += f"🎯 **Avlod genotiplari (F₁):**\n"
        for g, c in gen_counts.items():
            pct = (c / total) * 100
            res += f"• `{g}`: {c}/{total} qism ({pct:.1f}%)\n"
            
        return res

# Dvigatellarni ishga tushirish
math_engine = AdvancedMathEngine()
chem_engine = ChemistryEngine()
bio_engine = BiologyEngine()

# ==============================================================================
# TELEGRAM BOT HANDLERS
# ==============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = (
        f"Salom, **{user.first_name}**! **MegaScience AI Engine** tizimiga xush kelibsiz! 🚀\n\n"
        "Men Matematika, Kimyo va Biologiya masalalarini bosqichma-bosqich yechib beraman:\n\n"
        "📐 **MATEMATIKA:**\n"
        "• `2x - 6 = 0` (Bosqichma-bosqich yechim)\n"
        "• `hosila: x^3 - 4x` (Hosilani qadam-baqadam olish)\n"
        "• `integral: x^2, 0, 3` (Integral yechimi)\n"
        "• `limit: (x^2 - 1)/(x - 1), 1` (Limit yechimi)\n"
        "• `matritsa: [[1, 2], [3, 4]]` (Matritsa tahlili)\n"
        "• `yigindi: 2*n + 1, 1, 5` (Yig'indi ∑)\n"
        "• `grafik: x^2 - 4` (Ox va Oy o'qlari bilan koordinatada chizish)\n\n"
        "🧪 **KIMYO:**\n"
        "• `kimyo: H2SO4` (Molyar massa va tarkib)\n"
        "• `tezlik: 0.8, 0.2, 10` (Reaksiya tezligi: C1, C2, t)\n"
        "• `organika: alkan, 5` (Organik birikma va yonish reaksiyasi)\n\n"
        "🧬 **BIOLOGIYA:**\n"
        "• `atf: 5` (Glyukoza energiyasi balansi va ATF)\n"
        "• `fotosintez: 180` (Fotosintez sarf-xarajati)\n"
        "• `dnk: ATGCGATCG` (DNK, i-RNK, vodorod bog'lar)\n"
        "• `genetika: Aa x Aa` (Monogibrid chatishtirish)"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    try:
        # KIMYO: TEZLIK
        if text.lower().startswith("tezlik:"):
            parts = [float(p.strip()) for p in text.split(":", 1)[1].split(",")]
            res = chem_engine.process_kinetics(parts[0], parts[1], parts[2])
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # KIMYO: ORGANIKA
        if text.lower().startswith("organika:"):
            parts = [p.strip() for p in text.split(":", 1)[1].split(",")]
            res = chem_engine.process_organics(parts[0], int(parts[1]))
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # KIMYO: MOLYAR MASSA
        if text.lower().startswith("kimyo:"):
            formula = text.split(":", 1)[1].strip()
            res = chem_engine.calculate_molar_mass(formula)
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # BIOLOGIYA: FOTOSINTEZ
        if text.lower().startswith("fotosintez:"):
            val = float(text.split(":", 1)[1].strip())
            res = bio_engine.process_photosynthesis(val)
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # BIOLOGIYA: ATF
        if text.lower().startswith("atf:"):
            val = float(text.split(":", 1)[1].strip())
            res = bio_engine.process_atf(val)
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # BIOLOGIYA: DNK
        if text.lower().startswith("dnk:"):
            seq = text.split(":", 1)[1].strip()
            res = bio_engine.process_dna(seq)
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # BIOLOGIYA: GENETIKA
        if text.lower().startswith("genetika:"):
            p_gen = text.split(":", 1)[1].strip()
            res = bio_engine.process_genetics_monohybrid(p_gen)
            await update.message.reply_text(res, parse_mode="Markdown")
            return

        # MATEMATIKA ENGINE
        res_type, result, extra = math_engine.process_query(text)
        if res_type == "both":
            text_res, img_buf = result
            await update.message.reply_photo(photo=img_buf, caption=f"👤 **{user.first_name}** uchun yechim:\n\n{text_res}", parse_mode="Markdown")
        elif res_type == "graph":
            await update.message.reply_photo(photo=result, caption=f"📈 **{extra}** funksiya grafigi (Ox va Oy o'qlari bilan)")

    except Exception as e:
        await update.message.reply_text(f"❌ **Xatolik:** `{str(e)}`", parse_mode="Markdown")

# ==============================================================================
# MAIN EXECUTION (FOR RENDER DEPLOYMENT & LOCAL EXECUTION)
# ==============================================================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--------------------------------------------------")
    print("MegaScience AI Engine (Math + Chem + Bio) Serverda Ishlamoqda...")
    print("--------------------------------------------------")
    app.run_polling()
