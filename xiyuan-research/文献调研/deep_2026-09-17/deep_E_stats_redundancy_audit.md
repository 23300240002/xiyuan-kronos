# Deep Research E · 统计/信息论冗余审计 + θ<1/2 缺口攻关（2026-09-17）

> 审计对象：`research/reports/crossmodal_derivation_from_scratch.tex`（第 0–19 层）、
> `research/claims/C-CM-001.md`、`C-CM-004.md`（§1.5–1.6、§3.3、"失效边界"§3.4）、`C-T9-002.md`（R2 小 SNR 系数）、
> `C-X03-001.md`（§1 [待核] 引用）。
> 本文件不修改任何项目文件；只提出砍/留/改建议 + 可粘贴的引用条目。

## 0. 方法

**web_fetch 可用（已核实）**。抓取清单与状态：

| 源 | 状态 | 用于 |
|---|---|---|
| ar5iv.labs.arxiv.org/html/cs/0412108（Guo–Shamai–Verdú 2005 预印本 HTML） | 200 OK | I-MMSE 主定理、低 SNR 展开 |
| arxiv.org/pdf/cs/0412108 → 本地解析（22 页全文文本） | 200 OK，逐字提取 | Thm 1 (15)、Cor 1、Cor 2 (48)–(50)、(86)、Lemma 1 (29)、Thm 2 (22)、高斯输入最优性段、参考文献表 |
| arxiv.org/pdf/1004.3332 → 本地解析（Guo–Wu–Shamai–Verdú 2010） | 200 OK | Prop 1–4（MMSE 基本性质、**Prop 3 = 增量信道/SNR 相加**）、Prop 10（MMSE 对输入分布凹） |
| palomar.home.ece.ust.hk/papers/2006/PalomarVerdu_TransIT2006_gradI_vectorGMMSE.pdf → 本地解析 | 200 OK（页眉印 "VOL. 52, NO. 1, JANUARY 2006 141"） | Thm 1 (17)、Thm 2 (21)–(26)、Cor 1 (42)–(45)、**Thm 4 矩阵版多元 de Bruijn 恒等式** (55)–(57) |
| public.econ.duke.edu/…/Hansen-Lunde-2005.pdf → 本地解析（58 页工作稿） | 200 OK | **Lemma 4：E[RV^(m)] = IV + 2mω²**、Assumption 1/3、签名图史（Fang 1996 / ABDL 2000b）、参考文献表（Zhou 1996、Bandi–Russell 2005） |
| econpapers.repec.org（Bandi & Russell, ReStud 75(2)） | 200 OK | 卷期页 + 摘要逐字 |
| web.mit.edu/Alo/www/Papers/lo-mackinlay-88.html | 200 OK | Lo–MacKinlay 1988 书目条目 + 摘要逐字 |
| galton.uchicago.edu/~mykland/paperlinks/p1394.pdf（Zhang–Mykland–Aït-Sahalia 2005） | 200 OK，本地解析 | 确认**该文不含** "signature" 一词（用于排除误引） |
| jstor.org/stable/20185035、academic.oup.com/restud/article-pdf/… | 403 / reCAPTCHA | 未取正文 → 相关条目降为 [二手] |
| cs-114.org 的 Cover & Thomas 2nd ed. 全 PDF | 36 MB 超限 | **CT2 的定理编号未能核实** → 见 §5 |
| arxiv.org/pdf/1101.3455 | 抓到的不是目标论文（math.CO） | Bouchaud–Donier 签名图条目放弃，改用 Hansen–Lunde |

标注约定：**[一手]** = 我打开了承载该陈述的原文（或其官方书目页）并逐字抄录；
**[二手]** = 条目/编号来自另一篇论文的参考文献表或索引页，未打开原文。
每条外部结论：作者/年份/出处 + 英文原文逐字 + 一句话项目含义。

---

## 1. 逐恒等式审计表

| # | 恒等式(项目记号) | 标准出处(作者/年份/定理号) | 判定 | 若保留，引用行怎么写 |
|---|---|---|---|---|
| (1) | 第 2 层：$g^*(L)=\E[Y\mid L]$，$R_L^*=\E[(Y-\E[Y\mid L])^2]$（L² 投影 + 交叉项为零） | **现代带编号表述（已核）**：Guo–Shamai–Verdú 2005, eq. (9) 与其前句 "It is well-known that the minimum value of (8) … is achieved by the conditional mean estimator" [一手]；概率教材版：Durrett, *Probability: Theory and Examples*, 5th ed., Cambridge 2019, §4.1, **Thm 4.1.8**（条件期望在 $\sigma(L)$-可测函数中最小化均方误差）[二手] | **砍**（教科书定理，非项目内容） | `平方损失下的可测最优预测器是条件期望（a.s. 唯一），见 Durrett (2019, §4.1, Thm 4.1.8)；其信道论表述见 Guo–Shamai–Verdú (2005, eq. (9))。本文直接引用，不重推。` |
| (1b) | 第 4 层核心恒等式 $R_L^*-R_{L,H}^*=\E[(m_H-m_L)^2]=\Var(m_H)-\Var(m_L)$；等号条件 $m_H=m_L$ a.s. | 同上 + 全方差公式（条件版 P4，任何测度论教材；未取编号→§5）。同一式在 IT 文献中即 "MMSE 与条件方差的面积关系" 的差分形式 | **砍**（3 行化简，留结论 + 留 §4.6 "不能推出什么" 7 条） | `该式是全方差公式的直接推论（Durrett 2019, Thm 4.1.8 + 条件方差分解）。本项目不主张新颖性；其价值在 §4.6 的边界清单。` |
| (2) | 第 3 层：$\mathcal G\subseteq\mathcal G'\Rightarrow R^*(\mathcal G)\ge R^*(\mathcal G')$；"加信息风险不增、压信息风险不减" + 压缩链 $R^*_{Z_L}\ge R^*_L\ge R^*_{L,H}\le R^*_{Z_LZ_H}$ | 单调性部分：同 (1) 投影定理。右端 $\le$ 的部分 = **数据处理不等式**（Cover & Thomas 2nd ed., Thm 2.8.1 [二手，编号未核]）。SNR 版本（同一性质的连续参数形式）：**Guo–Shamai–Verdú 2005, Thm 1 + Cor 1** [一手] | **砍**（教科书；但**保留** §3.2 的项目结论"原始层闭式对神经网络编码器只是上界参照"，那不是定理而是接口判断） | `信息包含关系的单调性是条件期望投影性质的直接推论（Durrett 2019, Thm 4.1.8）；其 SNR 参数化形式即 Guo–Shamai–Verdú (2005, Thm 1, eq. (15)) 与 Corollary 1。压缩一侧即数据处理不等式。` |
| (3) | 第 6–10 层模型 D 四闭式：$R_H=1-\frac{u^2}{1+\nu}$、$R=1-\frac{2u^2}{2+\nu-\theta}$、$D=2(\theta+\nu)$、$u^2=\frac{(\sqrt{1-\theta}+\kappa\sqrt\theta)^2}{1+2\kappa^2}$、$R_H-R=\frac{u^2(\nu+\theta)}{(1+\nu)(2+\nu-\theta)}\ge0$ | **联合高斯条件协方差 / 线性 MMSE**：Guo–Wu–Shamai–Verdú 2010, Prop 1–3（eq. 18–22）[一手]；向量高斯信道 MMSE 矩阵：Guo–Shamai–Verdú 2005, **Thm 2 (22)** + 其"高斯输入情形直接验证"段（该文 5 页，eq. (22) 后）[一手]；相关噪声下的合并 = Palomar–Verdú 2006, Thm 2 (21)–(26)（对 $\Sigma_x,\Sigma_n$ 的导数）[一手]；$\Delta I=\frac12\ln\frac{R_H}{R}$：高斯条件互信息 $=\frac12\ln\frac{\Var(T\mid Z_H)}{\Var(T\mid Z_H,Z_L)}$（教科书结果，CT2 编号未核→§5；**已核的等价单字母陈述**：Guo–Shamai–Verdú 2005, eq. (11) $I(\mathsf{snr})=\frac12\log(1+\mathsf{snr})$ 与 eq. (13) $\mathsf{mmse}(\mathsf{snr})=\frac{1}{1+\mathsf{snr}}$，见 §1(A2) [一手]）；向量版条件协方差 $R=1-c^\top\Sigma_Z^{-1}c$ 的教科书定理号 = Kay (1993) **Thm 11.1**（经 Palomar–Verdú 2006 eq. (15) 之引用取得）[二手] | **应用**（保留推导，但压成"代入 $\Sigma_Z,c$"的 6 行 + 标准引用；**保留** §"结果 1 的勘误：原稿 $u^2$ 错" 与 第 9.3 "红线"，这两处是项目内部治理内容） | `四闭式是联合高斯条件方差公式（线性 MMSE）在对称两路结构下的代入，标准形式见 Guo–Wu–Shamai–Verdú (2010, Prop. 1–3) 与 Guo–Shamai–Verdú (2005, Thm. 2)；\Delta I 的对数形式是高斯互信息的条件方差比表示。本项目的贡献限于 (i) 该机制与 $L_{\rm align}$ 的对应审查（X-10）与 (ii) $u^2$ 的勘误，不含公式本身。` |
| (4) | **$\Delta I(\theta)$ 在 $\theta<1/2$ 段严格递增**（$\kappa=1$，任意 $\nu>0$；项目现标 CONJECTURED） | **未找到覆盖它的现成定理**（§2 列检索面）。最接近的三个工具：GSVD 2005 Thm 1（单参数 SNR 单调/凹）[一手]；GWsv 2010 **Prop 3**（两路**独立**信道的 SNR 相加）[一手]——其前提在本模型**不成立**；Palomar–Verdú 2006 Thm 4 / Cor 1（对协方差矩阵求导的矩阵 de Bruijn）[一手]——给导数不给符号 | **新**（项目内命题，且**可用 6 行代数自行证明**——见 §2.4 的候选引理，已机器核验；**不需要**文献授权） | `命题 C（$\Delta I'>0$ 于 $[0,\theta_0]$）为本工作在模型 D 内的新结果；证明见 §2.4 引理（其 $\theta<1/2$ 段由 $N(\theta,\nu)$ 的四项非负分解给出）。与 $\theta\ge1/2$ 段合并即覆盖整个 $[0,\theta_0]$。` |
| (5) | C-T9-002 R2/勘误 1：$I=\dfrac{m^2}{8\sigma^2}+o(m^2)$ nats（$r:=\dfrac{m^2}{4\sigma^2}$ 为 SNR，$I/r\to\frac12$） | **Guo–Shamai–Verdú 2005, Lemma 1 (29) + eq. (86)** [一手]；低 SNR 斜率的通行表述：**Verdú 2002, "Spectral efficiency in the wideband regime," IEEE T-IT 48:1319–1343**（= GSVD 的参考文献 [3]）[一手（该条目见 GSVD 参考文献表）] | **应用**（保留"1 行代入 + 回归测试 R2"，删掉独立重推） | `小 SNR 展开直接取自 I-MMSE 关系：\lim_{\mathrm{snr}\to0}\mathrm{mmse}=\sigma_X^2（Guo–Shamai–Verdú 2005, eq. (86)）与 I(\mathrm{snr})=\frac{\mathrm{snr}}{2}\Var(X)+o(\mathrm{snr})（同文 Lemma 1, eq. (29)）。本模型 X=\pm1 等概故 \Var=1，\mathrm{snr}=r=m^2/(4\sigma^2)，得 I=m^2/(8\sigma^2)+o(m^2)。` |
| (6) 附加 | C-T9-002 定理 1：$B=A+I$，$\E_Y\mathrm{KL}(q(z\mid y)\,\Vert\,p(z))=I(Y;Z)+\mathrm{KL}(q(z)\,\Vert\,p(z))$ | 相对熵链式法则 + "互信息 = 条件 KL 对标签的期望"（变分信息瓶颈里的标准分解）。**编号出处未核**（见 §5） | **砍**（三行代数；项目已自己标【既有结果】，只缺引用） | `\E_Y\mathrm{KL}(q(\cdot\mid y)\|r)=I(Y;Z)+\mathrm{KL}(q\|r)` 是 KL 链式法则的直接推论（标准分解，见信息瓶颈/VIB 文献中的率分解）。 |
| (7) 附加 | 命题 O：$\delta\uparrow\Rightarrow D(\hat\theta_\delta)\downarrow,\ R(\hat\theta_\delta)\uparrow$（+ $\theta_2\le\theta_1$） | 正则化路径/Tikhonov 泛函的初序单调性——**未找到带编号的权威出处**（属"两行相减"级引理，任何多目标优化教材的练习级结论）。判定按"教科书标准，但作者自证成本更低" | **砍重推、留 3 行证明 + 标【既有工具】**（项目现状已正确；注意 §2.5：$d\theta/d\delta\le0$ **已被命题 O 的证明覆盖**，C-CM-004 §4 把它列为"数值观察"是**低估了自己**） | `命题 O 是加权目标路径的标准单调性（两行相减证明）；本项目保留证明而不作新颖性主张。` |

**逐字依据（表内引用的核心原文）**

**(A) I-MMSE 主定理** — Guo, Shamai (Shitz) & Verdú, "Mutual information and minimum mean-square error in Gaussian channels," *IEEE Trans. Inform. Theory* **51**(4): 1261–1282, Apr. 2005（DOI 10.1109/TIT.2005.844072；预印本 arXiv:cs/0412108。⚠️ 本轮任务书写作"2006"，正确出版年份为 **2005**（项目 C-T9-002 §10.3 已写 2005，无需改）；页码取自索引记录 [二手]，正文为我打开的预印本全文 [一手]——预印本与刊出版公式编号可能相差 ≤1，正式引用公式号请以刊出版复核）：

> "**Theorem 1:** Let $N$ be standard Gaussian, independent of $X$. For every input distribution $P_X$ that satisfies $\mathsf{E}X^2<\infty$,
> $\dfrac{\mathrm{d}}{\mathrm{d}\mathsf{snr}}I\!\left(X;\sqrt{\mathsf{snr}}\,X+N\right)=\dfrac12\,\mathsf{mmse}\!\left(X\mid\sqrt{\mathsf{snr}}\,X+N\right).$ (15)"

> "The following corollaries are immediate from Theorem 1 together with the fact that $\mathsf{mmse}(\mathsf{snr})$ is monotone decreasing.
> **Corollary 1:** The mutual information $I(\mathsf{snr})$ is a concave function in $\mathsf{snr}$.
> **Corollary 2:** The mutual information can be bounded as $\mathsf{E}\{\mathrm{var}\{X\mid Y;\mathsf{snr}\}\}=\mathsf{mmse}(\mathsf{snr})$ (48) $\le \frac{2}{\mathsf{snr}}I(\mathsf{snr})$ (49) $\le \mathsf{mmse}(0)=\mathrm{var}\{X\}.$ (50)"

> "$\lim_{\mathsf{snr}\to0}\mathsf{mmse}(\mathsf{snr})=\mathsf{mmse}(0)=\sigma_X^2$ (86)"
> "**Lemma 1** As $\delta\to0$, the input–output mutual information of the canonical Gaussian channel … is given by $I(Y;Z)=\frac{\delta}{2}\mathsf{E}(Z-\mathsf{E}Z)^2+o(\delta).$ (29)"
> （渠道模型定义在 eq. (3)：$Y=\sqrt{\mathsf{snr}}\,X+N$；全文以 nats 为单位。）

*项目含义*：项目的 (2)（信息↑⇒MMSE↓）与 (5)（$I=r/2+o(r)$）都是上述两行的**代入**；(5) 的 $1/8$ 系数即 $\frac12\cdot\frac14$，与项目 R2 回归（$I/r\to0.49999975$）一致。注意 PDF 抽取使 (50) 一度显示为 `var{X^2}`，那是提取伪影，正确为 $\mathrm{var}\{X\}$。

**(A2) 同一篇论文里对 (1) 与 (3) 的"带编号现成表述"**（该文 §II，eq. (8)–(14)）[一手]：

> "It is well-known that the minimum value of (8), referred to as the minimum mean-square error or MMSE, **is achieved by the conditional mean estimator:** $\hat X(Y;\mathsf{snr})=\mathsf{E}\{X\mid Y;\mathsf{snr}\}.$ (9)"
> "To start with, consider the special case when the input distribution $P_X$ is standard Gaussian. The input-output mutual information is then the well-known channel capacity under input power constraint [25]: $I(\mathsf{snr})=\frac12\log(1+\mathsf{snr}).$ (11) Meanwhile, the conditional mean estimate of the Gaussian input is merely a scaling of the output: $\hat X(Y;\mathsf{snr})=\frac{\sqrt{\mathsf{snr}}}{1+\mathsf{snr}}Y,$ (12) and hence the MMSE is: $\mathsf{mmse}(\mathsf{snr})=\frac{1}{1+\mathsf{snr}}.$ (13)"

⟹ 项目的 $R_H=1-\frac{u^2}{1+\nu}=\frac{1+\nu-u^2}{1+\nu}$ 正是 (13) 在"先验方差 1、观测系数 $u$、噪声 $1$"归一化下的写法（$\mathsf{snr}=u^2/(1+\nu-u^2)$ 时 $\frac{1}{1+\mathsf{snr}}$ 乘回 $\Var(W_H)$ 即得）；$\Delta I=\frac12\ln\frac{R_H}{R}$ 的对数形式即 (11) 型的"高斯互信息 = ½log(1+snr)"之差。
向量版（项目的 $2\times2$ 求逆）在 Palomar–Verdú 2006 中的对应物 [一手]：

> "the covariance of the conditional mean estimation error is (e.g., **[7, Theorem 11.1]**)" —— 其中 [7] = "S. M. Kay, *Fundamentals of Statistical Signal Processing: Estimation Theory*. Englewood Cliffs, NJ: Prentice-Hall, 1993."

⟹ 想要一条**教科书定理号**给 $R=1-c^\top\Sigma_Z^{-1}c$（项目 G1），Kay (1993) Thm 11.1 是可核的落点（我核到的是 Palomar–Verdú 对该定理号的引用与其用途，未打开 Kay 原书页码 → Kay 定理号标 [二手]）。

*项目含义*：(1)(2)(3)(5) 四条**全部**落在这一篇论文的编号公式里，本项目的重推没有任何信息增量。

**(B) 两路观测的信息分解** — Guo, Wu, Shamai (Shitz) & Verdú, "Estimation in Gaussian noise: properties of the minimum mean-square error," *IEEE Trans. Inform. Theory* (2010)（arXiv:1004.3332）[一手]：

> "It has long been noticed that **two independent looks through Gaussian channels is equivalent to a single look at the sum SNR**, e.g., in the context of maximum-ratio combining. As far as the MMSE is concerned, the SNRs of the direct observation and the side information simply add up.
> **Proposition 3:** For every $X$ and every $\mathsf{snr},\gamma\ge0$, $\mathsf{mmse}(X,\gamma\mid\sqrt{\mathsf{snr}}X+N)=\mathsf{mmse}(X,\mathsf{snr}+\gamma)$ (22)"
> "**Proposition 1:** For every random variable $X$ and $a\in\mathbb R$, $\mathsf{mmse}(X+a,\mathsf{snr})=\mathsf{mmse}(X,\mathsf{snr})$ (18). **Proposition 2:** $\mathsf{mmse}(aX,\mathsf{snr})=a^2\mathsf{mmse}(X,a^2\mathsf{snr})$ (19). **Proposition 4:** $\mathsf{mmse}(X,\mathsf{snr})\le\min\{\mathrm{var}\{X\},1/\mathsf{snr}\}$ (26)."
> "**Proposition 10:** The functional $\mathsf{mmse}(X,\mathsf{snr})$ is concave in $P_X$ for every $\mathsf{snr}\ge0$."

*项目含义*：模型 D 的 $\Delta I$ 正是"第二路观测的增量信息"，而 Prop 3 的**独立性前提在本模型不成立**（§2.3）——这就是缺口无法用引用关闭的准确原因。

**(C) 对协方差矩阵求导 / 矩阵 de Bruijn** — Palomar & Verdú, "Gradient of mutual information in linear vector Gaussian channels," *IEEE Trans. Inform. Theory* **52**(1): 141–154, Jan. 2006（页眉自印 "VOL. 52, NO. 1, JANUARY 2006 141"）[一手]：

> 摘要逐字："…we show that **the gradient of the mutual information with respect to the channel matrix is equal to the product of the channel matrix and the error covariance matrix of the best estimate of the input given the output.** Gradients and derivatives with respect to other parameters are then found via the differentiation chain rule."
> "**Theorem 4 (Matrix Version of the Multivariate De Bruijn's Identity):** Consider an arbitrary random variable (with finite second-order moments) … contaminated with a Gaussian noise independent of … and with positive definite covariance matrix … (55)–(57)"
> "Observe that (43) is decreasing in [noise covariance] (since decreasing the noise variance improves the MMSE), which implies that … is an (increasing) concave function."（Corollary 1 后评注，数学式在 PDF 抽取中丢失）
> 同族可引：**Payaró & Palomar**, "Hessian and concavity of mutual information, differential entropy, and entropy power in linear vector Gaussian channels," *IEEE T-IT* **55**(8): 3613–3628, Aug. 2009 [二手（条目取自 danielppalomar.com 论文列表）]。

*项目含义*：这是"ΔI 对 $\theta$ 求导"的**标准机器**：$\theta$ 只通过 $\Sigma_Z$、$c$ 进入，故 $\frac{d\Delta I}{d\theta}$ 可由链式法则写成闭式（项目 §1.5 已经这么做了）。但该工具只给导数表达式，不给符号。

---

## 2. θ<1/2 段缺口攻关

### 结论先行：**未覆盖** —— 经典文献里没有任何定理直接推出它；**但它不需要文献**：一个四行代数引理即可关闭（下 §2.4，已机器核验）。

### 2.1 翻译成标准语言

模型 D（$\kappa=1$）里，$T_\kappa$ 方差为 1，两路观测与 $T$ 的协方差同为 $u(\theta)$，故可精确写成
$$Z_H=u(\theta)\,T+W_H,\qquad Z_L=u(\theta)\,T+W_L,$$
其中（Monte-Carlo 核验，$4\times10^6$ 抽样，见 §2.6）
$$\Cov(T,W_H)=\Cov(T,W_L)=0\ (\Rightarrow W_H,W_L\perp T\ \text{，高斯}),\quad \Var(W_H)=1+\nu-u^2,\quad \Cov(W_H,W_L)=\underbrace{(1-\theta)-u^2(\theta)}_{\text{记作 }b(\theta)} .$$
即：**"用两路相关噪声的高斯信道观测一个高斯标量，问其增量互信息关于设计参数 $\theta$ 是否单调。"** 标准语言里对应三个对象：

| 标准工具 | 陈述（逐字见 §1(A)(B)(C)） | 能否直接推出 $\theta<1/2$ 段 |
|---|---|---|
| I-MMSE（GSVD 2005 Thm 1 + Cor 1） | $I(\mathsf{snr})$ 关于**标量 SNR** 递增且凹；$\mathsf{mmse}(\mathsf{snr})$ 递减 | **否**。它只处理"单一 SNR"这一个旋钮。本模型 $\theta$ 同时移动三个量：每路 SNR $\frac{u^2}{1+\nu-u^2}$、两路噪声相关 $b(\theta)$、以及两路联合信噪比。不存在"SNR 随 $\theta$ 单调"这个前提 |
| 两独立信道 SNR 相加（GWsv 2010 Prop 3 (22)） | "two **independent** looks … the SNRs … simply add up" | **否**，前提失败：$b(\theta)\ne0$ 对一切 $\theta<1$（$\nu=0.7$ 实测 $b(0.05)=+0.47$、$b(0.5)=-0.17$）。合并后的有效 SNR 是**白化合并** $\mathrm{SNR}_{\rm eff}=\frac{2u^2}{(1+\nu-u^2)+b(\theta)}$ 而非相加 $\frac{2u^2}{1+\nu-u^2}$ |
| 矩阵 de Bruijn / 对 $\Sigma_x,\Sigma_n$ 的梯度（Palomar–Verdú 2006 Thm 2、Thm 4） | 给 $\partial I/\partial\Sigma$ 的闭式与"噪声方差↓⇒$I$↑且凹"的评注 | **部分**：它给出 $\frac{d\Delta I}{d\theta}$ 的合法推导路径（项目 §1.5 已实现），但**符号仍需自证**，且该文没有"相关系数↑⇒$I$↓"在**输入协方差同时变化**时的定理 |
| Loewner/数据加工序（"更噪声=更差信息"） | 若 $\Sigma_1\succeq\Sigma_2$ 则 $Z_1=\!Z_2+$ 独立高斯，$I(X;Z_1)\le I(X;Z_2)$（数据处理不等式） | **否**。$\theta$ 族在 Loewner 序下**不可比**：$u^2(\theta)=\frac{1+2\sqrt{\theta(1-\theta)}}{3}$ 在 $\theta=1/2$ 取最大（$2/3$），$\theta<1/2$ 段随 $\theta$ **上升**（每路自身信息变多，倾向压低 $\Delta I$），同时 $b(\theta)$ **下降**（两路更不冗余，倾向抬高 $\Delta I$）。两股反向力，任何"单调性序"都不成立 |

### 2.2 为什么"找不到定理"是结构性的，不是检索不足

$\theta<1/2$ 段上，分子 $R_H$ 与分母 $R$ **同时递减**（$(u^2)'>0$），故项目 §1.6 的 $\theta\ge1/2$ 论证（"两项均非负"）失效；被主张的量是**一个比值**的单调性，而两端各自信道/冗余的强度**朝相反方向变化**。现成的信息论单调性定理全部是"单旋钮 + 其他不动"的形式（SNR、噪声协方差的 Loewner 序、输入分布的凸序），没有一条覆盖"同一参数同时改信噪比与相关结构"的情形。这与 MIMO/分布式估计里"相关性对容量的影响非单调"的常识一致（该项目在此不引专门结论，仅作判断说明）。

### 2.3 还差哪一步（精确定位）

把 $\Delta I$ 化到一变量形式（**本文件的推导，非文献**，记号与项目一致，$\kappa=1$，$w:=\sqrt{\theta(1-\theta)}$，$u^2=\frac{1+2w}{3}$）：
$$\Delta I(\theta)=\tfrac12\ln\frac{(2+3\nu-2w)(2+\nu-\theta)}{(1+\nu)\,(4+3\nu-3\theta-4w)} .$$
（等价地，用**偏相关**表述：$\Delta I=\tfrac12\ln\frac{1}{1-\rho_p^2}$，$\rho_p^2=\frac{u^2(\nu+\theta)}{(1+\nu-u^2)(2+\nu-\theta)}$——高斯三元组条件互信息 = 偏相关的标准恒等式，数值核对：$\theta\in(0,1)$ 各 $2\times10^4$ 点、$\nu\in\{0.05,0.2,0.7,1,3\}$，与 $\frac12\ln(R_H/R)$ 最大差 $3.6\times10^{-15}$。）
"还差的一步"= 证明 $\frac{d}{d\theta}\Delta I>0$ 于 $(0,\tfrac12)$，即
$$\underbrace{-\frac{2w'}{2+3\nu-2w}}_{\text{每路 SNR 上升（}<0\text{）}}\underbrace{-\frac{1}{2+\nu-\theta}}_{<0}\;+\;\underbrace{\frac{3+4w'}{4+3\nu-3\theta-4w}}_{>0}>0,\qquad w'=\frac{1-2\theta}{2w}>0 .$$
——一个**一正两负**的三角/代数不等式（正项必须压住两个负项），不是任何现成定理的特例。

### 2.4 候选引理（缺口可关闭；建议项目独立复核后用它替换 CONJECTURED 标签）

通分后（sympy 符号求导，与中心差分对照相对差 $\le 9.9\times10^{-9}$）：
$$\frac{d\Delta I}{d\theta}=\frac{N(\theta,\nu)}{2\sqrt{\theta(1-\theta)}\,(\nu-\theta+2)\,(3\nu+2-2w)\,(3\nu+4-3\theta-4w)} ,$$
分母四个因子在 $\theta\in(0,1)$、$\nu>0$ 下**全为正**（第三个 $=3(1+\nu)R_H>0$，第四个 $=3(2+\nu-\theta)R>0$，恰好就是项目自己的 $R_H,R$）。分子可按**四项非负**分解：
$$\boxed{\,N(\theta,\nu)=\underbrace{3\nu^{2}(1-2\theta)}_{>0\ (\theta<1/2)}+\underbrace{6\nu\bigl(1+w-2\theta^{2}\bigr)}_{\ge 6\nu(1-2\theta^{2})\ge 3\nu>0}+\underbrace{4w\bigl(1-2w^{2}\bigr)}_{\ge 0\ (w\le 1/2)}+\underbrace{\theta\bigl(6\theta^{2}-19\theta+10\bigr)}_{>0\ (\theta<2/3)}\,}$$
- $w\le 1/2\Rightarrow 1-2w^2\ge 1/2\ge0$；
- $6\theta^2-19\theta+10=6(\theta-\tfrac23)(\theta-\tfrac52)>0$ 对 $\theta<\tfrac23$。

⟹ **对一切 $\nu>0$、$\theta\in(0,\tfrac12)$：$\frac{d\Delta I}{d\theta}>0$。$\theta<1/2$ 段可解析证明，无需文献、也无需 $\theta\le\theta_0$ 的限制。**

进一步数值证据（同一 $N$ 的精确导数，$\theta$ 网格 $4\times10^5$）：

| $\nu$ | $\theta_0=\arg\min_\theta R$ | $\Delta I'$ 的首个变号点 $\theta_{\rm cross}$ | $\theta_0<\theta_{\rm cross}$ | $\min_{[0,\theta_0]}\Delta I'$ |
|---|---|---|---|---|
| 0.001 | 0.79984 | 0.80008 | ✅ | +1.46e−1 |
| 0.01 | 0.79841 | 0.80076 | ✅ | +1.94e−1 |
| 0.2 | 0.77070 | 0.80512 | ✅ | +3.66e−1 |
| 1.0 | 0.69231 | 0.77140 | ✅ | +1.02e−1 |
| 3.0 | 0.60975 | 0.68838 | ✅ | +2.24e−2 |
| 10.0 | 0.54339 | 0.58376 | ✅ | +2.81e−3 |
| 100.0 | 0.50492 | 0.50983 | ✅ | +3.27e−5 |

*交叉验证*：本表 $\theta_0$（0.77070 / 0.69231 / 0.60975）与项目 C-CM-004 §1.3 的独立扫描（0.77070 / 0.69231 / 0.60976）**在网格分辨率内一致**（最大偏差 $1\times10^{-5}$，两侧网格步长分别约 $2.5\times10^{-6}$ 与 $2\times10^{-5}$）；§1.6 的 $\min_{[0,\theta_0]}\Delta I'$（0.366 / 0.102 / 0.022）与本表 3.66e−1 / 1.02e−1 / 2.24e−2 一致 → 说明本文件的模型读法与项目实现的是同一对象（这也是 §2.4 分解可信的前提）。

**对项目的直接后果（三条，均需项目自行复核后才可改状态）**：
1. C-CM-004 §3.3 / §4 缺口 1 的前半（$\theta<1/2$ 段）**可以关闭**；
2. §4 缺口 1 的后半"$\frac{d\theta}{d\delta}\le0$ 为数值观察"是**自我低估**：命题 O 的证明里 $D=2(\theta+\nu)$ 严格递增已给出 $\theta_2\le\theta_1$（tex 第 12.2 节的证明就写了这一步），它不是数值观察；
3. 于是**命题 C 整体可升级为定理**：定理 B 给 $\theta_\delta\in[0,\theta_0]$，命题 O 给 $\theta_\delta$ 随 $\delta$ 不增，$\Delta I'>0$ 于 $[0,\theta_0]$（§2.4 + 项目原有 $\theta\ge1/2$ 论证，或用 $\theta_{\rm cross}>\theta_0$ 的解析版本）⟹ $\Delta I(\theta_\delta)$ 沿 $\delta$ 不增。**注意**：这仍然只是"模型 D 内"的定理，不得升级为通用一致性对齐定理（§5 的"不允许据此声称"条款继续有效）。

### 2.5 若不愿自己证，退而求其次的引用姿态
把 $\Delta I'>0$ 写成"引理（证明：直接计算，见附）"，并在同一句里说明它与 I-MMSE 的关系不是推论而是类比：
> "The monotonicity is not an instance of the SNR-monotonicity of the MMSE (Guo–Shamai–Verdú 2005, Thm. 1): the parameter $\theta$ moves the per-channel SNR and the cross-channel noise correlation in opposite directions, and the two looks are not independent in the sense of Guo–Wu–Shamai–Verdú (2010, Prop. 3, eq. (22)) since $\mathrm{Cov}(W_H,W_L)=(1-\theta)-u^2(\theta)\neq0$."

这一句本身就是**新颖性的正面证据**（说明为什么必须自证），建议写进卡片而不是藏起来。

### 2.6 本文件自做的核验（全部可复跑）

| 核验 | 方法 | 结果 |
|---|---|---|
| $N(\theta,\nu)$ 分解 = sympy 导数分子 | 数值 20 万点 | 两者最大绝对差 $\le2.9\times10^{-13}$ |
| 解析导数 vs 中心差分 | $\nu=1$，$\theta\in[0.01,0.9]$ | 相对差 $\le9.9\times10^{-9}$ |
| $\Delta I$ vs $\frac12\ln\frac{1}{1-\rho_p^2}$（偏相关式） | $\nu=1$，多点 | 差 $<10^{-15}$（$\rho_p$ 式与 $R_H/R$ 式同物） |
| $Z_H=uT+W_H,\ W_H\perp T$；$\Var W_H=1+\nu-u^2$；$\Cov(W_H,W_L)=(1-\theta)-u^2$ | MC $4\times10^6$，$\theta\in\{0.05,0.3,0.5,0.8\}$，$\nu=0.7$ | $\Cov(T,W_\cdot)\le9\times10^{-4}$，其余吻合到 $2\times10^{-3}$ |
| 白化合并式 $R=\bigl(1+\frac{2u^2}{(1+\nu-u^2)+b}\bigr)^{-1}$ vs 项目闭式 $1-\frac{2u^2}{2+\nu-\theta}$ vs 样本回归 | 同上 | 三者一致（如 $\theta=0.3$: 0.468109 / 0.468109 / 0.467691） |

脚本位置为临时目录（未落项目仓库）；若需入库，建议另立 `research/scripts/verify_proposition_C.py`，**由项目自行实现并复跑**（本文件只报告结果，不充当验收）。

---

## 3. 模型 D 闭式的文献对应（公式 ↔ 标准结果 + 符号映射）

**符号映射表**（左：项目；右：标准文献记号）

| 项目 | 标准文献中的对应物 | 说明 |
|---|---|---|
| $T_\kappa$，$\Var(T)=1$ | 信道输入 $X$（GSVD）／高斯信号 $s$；$\Var=1$ = "先验精度 1" | 项目的"归一化到 1 使风险与解释方差同尺"= 标准做法 $R=\Var(T\mid Z)/\Var(T)$ |
| $Z_H,Z_L$ | 向量信道输出 $\boldsymbol{y}=H\boldsymbol{s}+\boldsymbol{n}$（Palomar–Verdú (8)–(9)）；GWsv 的 $\sqrt{\mathsf{snr}}X+N$ 与 side information | 本项目 $H=(u,u)^\top$，$\boldsymbol{n}\sim N(0,\Sigma_W)$，$\Sigma_W=\begin{pmatrix}1+\nu-u^2 & b\\ b & 1+\nu-u^2\end{pmatrix}$，$b=(1-\theta)-u^2$ |
| $\nu$ | 每路噪声方差（观测噪声 $N(0,\nu)$）；Aït-Sahalia–Jacod/Hansen–Lunde 的 $\omega^2$ 同属"与信号独立的观测噪声" | — |
| $\theta$ | 设计/编码参数：私有成分占比；在标准形式里**同时**是 $H$、$\Sigma_x$、$\Sigma_n$ 的函数 | 这是 (4) 无法引用定理的根源 |
| $u=\Cov(T,Z_H)$ | 信道增益 × 输入标准差；$u^2$ = 每路"解释方差"分子 | 项目 $u^2=\frac{(\sqrt{1-\theta}+\kappa\sqrt\theta)^2}{1+2\kappa^2}$ |
| $R_H=1-\frac{u^2}{1+\nu}$ | 标量高斯信道 $\mathsf{mmse}(\mathsf{snr})=\frac{1}{1+\mathsf{snr}}$（GSVD 2005 **eq. (13)**，标准高斯输入情形）[一手]；一般先验方差即 $\frac{\sigma^2}{1+\mathsf{snr}\sigma^2}$；等价地 = 高斯条件方差 $\Var(T)-\Cov^\top\Var(Z)^{-1}\Cov$（Kay 1993 Thm 11.1，经 PV 2006 (15) 引用）[二手] | **标准结果** |
| $R=1-\frac{2u^2}{2+\nu-\theta}$ | 相关噪声两路合并：$\bigl(1+2u^2/((1+\nu-u^2)+b)\bigr)^{-1}$（matched filter / 白化后 MRC），$\Cov(T\mid Z)=\bigl(1+\Sigma_W^{-1}\bigr)^{-1}$ 型精度相加 | **标准结果**（Gaussian conditioning / 线性 MMSE） |
| $R_H-R=\frac{u^2(\nu+\theta)}{(1+\nu)(2+\nu-\theta)}\ge0$ | "多一路不减信息"（数据处理 / 条件期望投影），即本审计的 (2) | 标准 |
| $\Delta I=\frac12\ln\frac{R_H}{R}$ | 高斯条件互信息 $=\frac12\ln\frac{\Var(T\mid Z_H)}{\Var(T\mid Z_H,Z_L)}$；等价 $\frac12\ln\frac{1+\mathsf{snr}_{\rm eff}}{1+\mathsf{snr}_H}$；亦即 $\frac12\ln\frac{1}{1-\rho_p^2}$（偏相关式） | **标准结果**（§5：CT2 编号未核） |
| $D=2(\theta+\nu)$ | 配对平方距离；= 两路观测噪声 + 私有分量差；无对应文献定理，**是项目自己的损失定义** | 保留 |
| $\theta_0=\arg\min R$、定理 B | 无对应文献（项目内的路径几何论证） | 保留 |

**"什么设定下 $\Delta I=\frac12\ln(R_H/R)$ 是标准的"**：仅当 $(T,Z_H,Z_L)$ 联合高斯（此时条件差熵 $=\frac12\ln(2\pi e\,\Var)$，$(2\pi e)$ 因子在比值中消去）。项目 tex 第 10 层的写法正确，但**必须**在陈述处写明"仅高斯"，且非高斯情形该式一般不成立（项目第 16 层已把它列入"条件性推导"✅）。

**并行高斯信道（parallel Gaussian channels）对应**：项目模型经对称/反对称旋转 $A=\frac{Z_H+Z_L}{\sqrt2}$、$B=\frac{Z_H-Z_L}{\sqrt2}$ 后，$B\perp T$（$\Cov(T,B)=0$ 且高斯），双路观测等价于**单个**标量观测 $A$（$\Var A=2+\nu-\theta$，$\Cov(T,A)=\sqrt2 u$）。这就是"并行信道/去相关化"的标准技巧（Cover & Thomas 的 parallel Gaussian channels 一节；编号未核，§5）。*项目含义*：模型 D 的双路结构实际只有一条有信息的路，$\theta$ 改变的是这条等效路的 SNR 与其和单路 $Z_H$ 的相关性——把它写进卡片可省掉第 8 层的 $2\times2$ 求逆。

---

## 3b. C-X03-001 签名图法标准出处（可直接粘进 §1 的引用条目）

**判定：**"RV 对 $1/\Delta$ 线性发散、斜率 $=2\omega^2$" 的规范出处**不是** Lo–MacKinlay；Lo–MacKinlay 是**方差比框架**（诊断"负一阶自相关/bounce"）的规范出处。两者覆盖本卡 §1 与 §2 的不同部分。可核的优先链：**Fang (1996, 未刊博士论文，首次导出该发散偏差) → Zhou (1996, JBES，该文献的期刊起点) → Bandi–Russell (工作稿 2005 / 正式 2008 ReStud) 与 Zhang–Mykland–Aït-Sahalia (2005 JASA) → Hansen–Lunde (2006 JBES, Lemma 4 给出与项目逐字同形的 $E[\RV^{(m)}]=\IV+2m\omega^2$)**。

可直接粘贴的段落（替换 C-X03-001 §1 末行"经典锚点 [待核]"）：

```text
经典锚点（已核）：
- 与项目 A1+A2 逐字对应的公式：Hansen, P. R. & Lunde, A. (2006), "Realized Variance and
  Market Microstructure Noise", Journal of Business & Economic Statistics 24(2), 127–158,
  **Lemma 4**（工作稿 July 2005 版逐字）："Given Assumptions 1 and 3.i-ii we have that
  E(RV^(m)) = IV + 2 m ω²"，其中 Assumption 3(ii) 定义 ω² ≡ E|u(t)|² < ∞、u 与 p* 独立
  （即本项目的 A2 观测噪声），m = T/Δ 为一日内收益根数 ⟹ 斜率 2ω² 对 T/Δ。
  同文 Lemma 4 的第二式 var(RV^(m)) = κ·12ω⁴m + …（即 Var 随 m 增大）是本项目 WLS 权重
  （Var RV(Δ) ∝ 1/n_blocks）的对偶依据：噪声主导部分随 m 线性增长。
- 该发散偏差的首次导出与命名：Hansen & Lunde 正文（§3）逐字："…this situation with
  independent market microstructure noise leads to a bias that diverges to infinity. This
  result was first derived in an unpublished thesis by Fang (1996). The expression for the
  variance, (2), is due to Bandi & Russell (2005) and Zhang et al. (2005)."
  → Fang, Y. (1996), "Volatility modeling and estimation of high-frequency data with
    Gaussian noise", Ph.D. thesis, MIT, Sloan School of Management. [未取原文，二手]
- 期刊起点：Zhou, B. (1996), "High-frequency data and volatility in foreign-exchange rates",
  Journal of Business & Economic Statistics 14(1), 45–52.（Hansen & Lunde §1："this
  literature was initiated by an article by Zhou (1996) that was published in this journal
  a decade ago"）[书目一手转引，正文未取]
- "volatility signature plot" 术语的正式出处（本卡"签名图"一词的出处）：
  Hansen & Lunde 逐字："Such plots first appeared in an unpublished thesis by Fang (1996)
  and were named and made popular by Andersen et al. (2000b)."
  → Andersen, T. G., Bollerslev, T., Diebold, F. X. & Labys, P. (2000b), "Great realizations",
    Risk 13(3), 105–108. [书目一手转引]
- 噪声-方差双尺度分解与"用签名图反推噪声矩"（本卡方法身份"方法应用（标准）"的真正对应物）：
  Bandi, F. M. & Russell, J. R. (2008), "Microstructure Noise, Realized Variance, and
  Optimal Sampling", Review of Economic Studies 75(2), 339–369（工作稿：Bandi & Russell
  (2005), "Microstructure noise, realized volatility, and optimal sampling", Working paper,
  GSB, University of Chicago）。摘要逐字："We show that, in the presence of market
  microstructure noise, realized variance does not identify the daily integrated variance …
  we demonstrate that the noise-induced bias at very high sampling frequencies can be
  appropriately traded off with the variance reduction obtained by high-frequency sampling
  and derive a mean-squared-error (MSE) optimal sampling theory … This naturally leads to an
  identification procedure, which allows us to recover the moments of the unobserved noise."
  → 最后一句就是本卡"由签名图斜率反推 ω"的标准表述。
- 方差比框架（本卡 §2 的 AR(1) 诊断 = bounce 期望为负 的规范出处）：
  Lo, A. W. & MacKinlay, A. C. (1988), "Stock Market Prices Do Not Follow Random Walks:
  Evidence from a Simple Specification Test", Review of Financial Studies 1, 41–66.
  摘要逐字："In this article we test the random walk hypothesis for weekly stock market
  returns by comparing variance estimators derived from data sampled at different
  frequencies…"
  ⚠️ Lo–MacKinlay **不提供** 斜率 = 2ω² 的标定式；它提供的是同族但另一侧的量：在 A1+A2 下
  Var(r_Δ) = σ²Δ + 2ω² ⟹ Var(r_Δ)/(σ²Δ) = 1/ρ(Δ)，且 VR(q) = ρ(Δ)/ρ(qΔ)，
  ρ₁(1min) = −ω²/(σ²Δ+2ω²) = −(1−ρ(Δ))/2。即本卡的 ρ 与 LM 的 VR/AR(1) 是同一二阶结构的
  三种再参数化——引用时分别标注（标定式引 Hansen–Lunde/Bandi–Russell；诊断式引 Lo–MacKinlay）。
- 已排除的误引：Zhang, Mykland & Aït-Sahalia (2005, JASA 100, 1394–1411) 全文**不含**
  "signature plot" 一词（已核其 PDF），且其贡献是多尺度修正而非斜率标定；本卡 §1 若引它，
  应表述为"噪声使 RV 偏差发散"的一般结论，不要写成签名图斜率的出处。
  （注：C-X03-001 现文 "Bandi & Russell (2006) 双尺度噪声分解" 的年份/标题未能核实，
  规范正式发表为 2008 ReStud；工作稿为 2003/2005。"Two-Scale Realized Volatilities"
  是 Bandi–Russell 的另一份早期工作稿标题，本次未取到可核版本 ⟹ 见 §5。）
```

---

## 4. `crossmodal_derivation_from_scratch.tex` 砍/留/改清单（逐节）

| 节 | 现内容 | 处置 | 理由（对应 §1 表行） |
|---|---|---|---|
| 第 0 层 舞台与记号 | 随机变量/期望/σ-代数/无泄漏 | **留**（记号定义，非定理） | — |
| 第 1.1 条件期望三种理解 | 离散/连续/测度论 | **改**：压到 4 行（只留测度论定义 + a.s. 说明），离散与连续版删 | (1) 砍；a.s. 一句是后面等号条件的纪律，必须留 |
| 第 1.2 性质 P1–P4 | 塔式/提出/全方差/条件全方差 | **改**：列成一条引用（"条件期望标准性质，见 Durrett 2019 §4.1"）；**P4（条件版全方差）单独留式**，因为第 4 层唯一真正用到它 | (1b) |
| 第 2 层 L² 投影定理（含交叉项证明） | 完整证明 | **砍证明，留结论框 + 一句"交叉项由塔式性质为零"** | (1)：教科书定理，重推无信息量 |
| 第 2.2 推论 $g^*=\E[Y\mid L]$ | 框 | 留（作为引用落点） | — |
| 第 3.1 风险链 $R^*_{Z_L}\ge R^*_L\ge R^*_{L,H}\le R^*_{Z_LZ_H}$ | 由 P4 推 | **改**：结论保留，推导删；两侧分别标"投影单调性"与"数据处理不等式" | (2) |
| 第 3.2 为什么"$H$ 有增量"推不出"$Z_H$ 有用" | 项目判断 | **留**（这是全稿最有价值的接口结论之一；只是它不是定理） | (2) 备注 |
| 第 4 层 核心恒等式 Step 1–5 | 5 步 | **砍**到 2 行（P4 直接给）；**§4.4 更漂亮的视角、§4.5 等号条件、§4.6 七条"不能推出什么"全部留** | (1b)；§4.6 是本项目的真实贡献（边界纪律） |
| 第 5–6 层 模型 D 构造 + 协方差手算 | 逐元展开 | **留构造、砍手算**：协方差改成"由 iid 双线性一行给出 $\Var Z_i=1+\nu$、$\Cov=\,(1-\theta)$"；**§6.2 的 $u^2$ 与"原稿写错的地方"标注必须留**（勘误是项目内部治理记录，不是数学贡献） | (3) 应用 |
| 第 7 层 $R_H$ | 正规方程 | **砍**：换成"标量高斯信道 $\MMSE=\sigma^2/(1+\mathsf{snr}\sigma^2)$，见 GSVD 2005 高斯输入特例"两行 | (3) |
| 第 8 层 $R$（$2\times2$ 求逆逐步） | 逐步 | **砍**（改 4 行）+ **建议加**：对称/反对称旋转使 $B\perp T$、双路等价于单路 $A$（§3 末），这既省求逆又是给读者的正确抽象 | (3) |
| 第 9.1 $R_H-R\ge0$ | 一行代数 | 留一行 + 标"即 (2) 的单调性" | (2)(3) |
| 第 9.2–9.3 一个必须记住的数 + 红线 | 数值 $R_H=\frac23,R=\frac7{15}$，低估 $\frac15$ | **留**（部署口径是项目问题，不是教科书内容） | — |
| 第 10 层 $\Delta I$ 推导 | 高斯熵 + 熵差 | **砍**成"$\Delta I=\frac12\ln\frac{\Var(T\mid Z_H)}{\Var(T\mid Z_H,Z_L)}$（高斯专属）+ 引用"；**§10.4 警告"$\Delta I$ 不含私有贡献"与 T6 回归点必须留** | (3) |
| 第 11 层 有限性 / $\nu\to0$ 路径依赖 | 两条路径表 | **留**（文献无此内容；与 C-CM-004 §3.4 同） | 项目内容 |
| 第 12.2 命题 O | 3 行证明 | **留证明 + 标【既有工具】**；**§12.2 末尾"$D=2(\theta+\nu)$ 得 $\theta_2\le\theta_1$"要提到正文**（它已被证明，却被 C-CM-004 §4 记成"数值观察"） | (7) |
| 第 12.3 定理 A / 定理 B | 已证 | **留**（模型内、便宜、且定理 B 的"不依赖凸性"是有用的方法论声明） | 项目内容 |
| **第 12.4 命题 C** | "仅数值支持" | **改**：按 §2.4 升级为已证（$\theta<1/2$ 段引 $N>0$ 的四项分解；$\theta\ge1/2$ 段沿用现有论证）；同时把"引用时必须写仅数值支持"改为"模型内定理，不外推"。**改动需项目自行复跑核验后再落地** | (4) |
| 第 13 层 $L_{\rm align}$ 病一/病二/反例/设计建议 | 项目分析 | **全留**；病一（缩放逃逸、下确界不取到）建议加一句与自监督/蒸馏里"平凡解/尺度退化"同族的说明，但不硬找引用 | 项目内容 |
| 第 14–15 层 路线表 / X-10 布尔路由 | 工程治理 | **全留** | — |
| 第 16 层 四类清单 | "待核验问题：X-06/X-09（命题 O、G1、G2、$B=A+I$、I–MMSE 文献出处未核验）" | **改**：X-09 的 I–MMSE 已核（本文件 §1(A)），G1/G2 属标准高斯条件方差/条件互信息（CT2 编号仍待核，见 §5），$B=A+I$ 为 KL 链式法则（编号待核）；把该项从"待核验"改为"已核（本文件），编号余项列 §5" | — |
| 第 17–19 层 | 项目改动建议 + 自检 | **留**；自检点 3、5 的答案改为指向 §3 的标准公式而非"自己推" | — |
| 全稿"未联网核验文献新颖性"声明（前言框） | — | **改**：改为"§1、§2 层（平方损失/单调性）、模型 D 闭式 (3)、小 SNR (5) 已核为教科书/标准结果（本文件 §1、§3、§3b）；$\theta<1/2$ 单调性 (4) 已核为**文献未覆盖、本项目可自证**（§2）" | — |

**净效果**：第 1–4、7–8、10 层可压掉约 45% 篇幅（原为教科书重推），腾出的位置用于 §2.4 的引理与 §3 的符号映射表；第 9.3、11、12、13、15、16、17 层全部保留——那些才是项目自己的东西。

---

## 5. 未能核实的点

| # | 未核实项 | 现状 | 建议动作 |
|---|---|---|---|
| 1 | Cover & Thomas 2nd ed. 的**定理编号**：(a) 高斯 $I(X;Y)=\frac12\ln\frac{\Var X}{\Var{X\mid Y}}$；(b) 并行高斯信道一节；(c) 数据处理不等式（我按记忆写为 Thm 2.8.1）；(d) 条件差熵 | 全 PDF 36 MB 超过抓取上限；未取到带编号的页面。**缓解**：(1)(3)(5) 的实质内容已改由 Guo–Shamai–Verdú 2005 的编号公式（eq. (9)、(11)–(13)、(15)、(29)、(86)）逐字覆盖，CT2 只作为"教科书出处"的可选替代 | 用纸质/电子版第 2、8、10 章补编号；**在此之前引用行只写章节名不写定理号**（我上表的引用行已按此纪律写） |
| 2 | Durrett "best predictor" 的**精确编号与版次**（5th ed. Thm 4.1.8；4th ed. 编号不同） | 依据是数学问答站该标题 + 5th ed. 目录（Ch.4 §1 = Conditional Expectation）→ [二手]。**已有一手的替代**：GSVD 2005 eq. (9) | 若坚持教材口径，打开 sites.math.duke.edu/~rtd/PTE/PTE5_011119.pdf 的 §4.1 复核；另一可选教科书锚点：Kay (1993) Thm 11.1（同 §1(A2)，我未打开 Kay 原书） |
| 3 | $B=A+I$（C-T9-002 定理 1）的**带编号出处** | 判定为 KL 链式法则的直接推论（数学上无争议），但我没有抓取到可粘贴的编号陈述 | 落到 CT2 §2.5/§8.2 或 VIB 文献（Bondarenko et al. / Shamir et al. 2020 的率分解），由项目挑一个 |
| 4 | Hansen & Lunde 正式版的**页码 127–158**（我抓的是 2005 年 7 月工作稿，Lemma 4 逐字取自该稿） | [二手] 页码 | 以 JBES 24(2) 2006 正式版核对页码与 Lemma 编号是否变动 |
| 5 | **"Bandi & Russell (2006)"这个条目本身**：项目 C-X03-001 现写的 2006 + "双尺度噪声分解"未在任何官方记录中命中；"Two-Scale Realized Volatilities" 疑为其早期工作稿标题 | 已确认的只有 2005 工作稿（GSB Chicago）与 2008 ReStud 75(2):339–369 | 卡片里删掉"2006"，改成 2008 ReStud；若确需 2006 版，须另找 SSRN 记录 |
| 6 | Zhou (1996) 与 Fang (1996) 的**原文公式**（我只从 Hansen–Lunde 的转引与参考文献表取得条目） | [二手转引] | 若要对外主张"优先权归属"，需打开 JBES 14(1):45–52 原文 |
| 7 | (4) 的**文献穷尽性**：我检索了 I-MMSE 单调性、de Bruijn/van Trees 家族、Palomar–Verdú 协方差导数、"MI 对相关系数单调"、两观测高斯合并；未检索到覆盖"θ 同时改 SNR 与相关结构"的定理。负命题无法穷尽 | 结论按"未覆盖"给出，并给了不依赖文献的自证路径 | 若项目要正式主张新颖性，建议再补一轮以 "distributed estimation correlated observations monotonicity value of side information" 为关键词的检索 + 询问导师/审稿人口径 |
| 8 | 我给出的 §2.4 引理是**本文件的推导**，不属于任何文献 | 已做 4 类机器核验（§2.6），分母正性依赖 $R_H,R>0$ | 项目必须**自行独立实现并复跑**后才可把命题 C 从 CONJECTURED 升级为已证（C-CM-004 §1.5 的实现 bug 教训：外部助手给出的证明不得自动标记通过） |
| 9 | C-T9-002 命题 4/定理 3 的 $\sigma=\tau$ 阈值、$\partial A/\partial r$ 公式 | 属本审计范围外的另一条线；其依赖的 I–MMSE 已核实（§1(A)），故该文"出处未核"的标签**现在可以解除**（改为 GSVD 2005 Thm 1 + eq (86)） | 更新 `state.json` X-06 |
| 10 | **Guo–Wu–Shamai–Verdú 2010（arXiv:1004.3332）的刊出版卷期页**（Prop 1–4 的编号取自 arXiv 版正文，我已逐字核对；刊出版为 IEEE T-IT 2010，具体页码未取到——该 PDF 内没有 journal 页眉，dblp 抓取被反爬墙挡住） | 公式号 (18)–(26) 来自 arXiv 版 [一手]；卷期页 [未核] | 正式引用前用 IEEE Xplore 核对卷期页；若只引 Prop 3 的思想，改引 GSVD 2005 的增量信道（该文已核到 51(4):1261–1282）|
