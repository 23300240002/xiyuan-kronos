# Deep Research B · 跨源/跨频表示对齐方法候选空间（2026-09-17）

| 字段 | 内容 |
|---|---|
| 关联任务 | TP9 / X-10 §7 的"实际 $L_{\text{align}}$ 能否写成配对平方一致性"——本文件给出**候选方法表**，不代替 X-10 的答复 |
| 目标 | 为 $(Z_L\in\mathbb R^{512},\;Z_H\in\mathbb R^{11})$ 的跨源（低频 Kronos hidden context ↔ 1min 盘口统计）对齐损失 $L_{\text{align}}$ 圈定**已发表**候选空间 |
| 判据接口 | DS-CM-001 的 `P/A/H/B/S` 五位（见 §1 每方法末行与 §2）；模型 D 的 $D=2(\theta+\nu),\,R_H,\,R,\,\Delta I$（C-CM-004 §2/§3） |
| 硬约束 | 全部候选必须已发表；禁止玩具式自造目标 |
| 抓取时间 | 2026-09-17（本文全部链接当日可达） |

---

## 0. 方法

**可达性**：`web_fetch` 可用（NO_WEB_ACCESS 不适用）。arXiv abs 页与 ar5iv 全文页均可达；arXiv API（`export.arxiv.org/api/query`）可达但有 429 限流；Semantic Scholar API 严重限流；arXiv 人肉检索页 `arxiv.org/search/` 从 shell 返回 400。

**抓取策略（本文件的取证方式）**：
1. **不用记忆中的 arXiv ID**。所有 ID 至少经 (a) arXiv API 标题/作者检索回显，或 (b) 直接 fetch `arxiv.org/abs/<ID>` 并核对返回标题。**多次记忆中的 ID 被证伪**（例：2006.02040 → 仓库自动机论文；2110.05136 → 自旋泵论文；2211.15009 → WMT 翻译系统论文）。
2. 逐字公式一律来自 ar5iv 渲染页（正文/`alttext`），**不转述、不改写**；无法逐字取到的条目在 §5 标 UNVERIFIED，不填"看起来对"的公式。
3. 并行两个只读取证子代理补 ID 核验（KCCA、Procrustes 跨维、DTW、representation-vs-prediction）。凡引文由子代理抓取、本文件作者未亲自复核原页者，一律标注 **[一手-子代理]**；其余为 **[一手]**。
4. 实际 fetch 过的 arXiv 页（本文引用主干）：
   `1807.03748`(CPC) · `2002.05709`(SimCLR) · `2005.10242`(Wang–Isola, 由子代理) · `2012.09740`(Wang–Liu) · `2102.08850`(Zimmermann et al.) · `2203.02053`(Liang et al. modality gap) · `1905.00414`(Kornblith CKA) · `1907.02893`(IRM) · `2405.19539`(Donnat–Tuzhilina CCA=RRR) · `2306.16393`(Bykhovskaya–Gorin) · `1503.01538`(PyrCCA) · `1705.04194`(Alam–Fukumizu–Wang) · `1304.7717`(RDC) · `1602.09013`(Podosinnikova–Bach–Lacoste-Julien) · `1610.00558`(Weighted Procrustes) · `2008.04631`(Procrustes 高维) · `1507.00825`(Ridge/Hubness) · `1412.6568`(Dinu) · `2006.03652`(FIPP) · `1812.10382`(Global Anchor) · `2101.05068`(PCME) · `2412.14113`(Adversarial Hubness) · `0805.2368`(MMD 两样本) · `1502.02791`(DAN) · `1705.10667`(CDAN) · `1904.05801`(MDD) · `1409.5241`(Subspace Alignment, 仅标题) · `1801.04062`(MINE) · `1811.04251`(McAllester–Stratos) · `1910.06222`(Song–Ermon) · `1911.02277`(CMINE) · `1804.07203`(Shah–Peters) · `1503.02531`(KD) · `1904.05068`(RKD) · `1907.09682`(SP) · `2402.19072`(TimeXer) · `2405.14616`(TimeMixer) · `2606.00624`(HANET) · `1808.09964`/`1903.01454`(DTW 非度量) · `1910.09153`(entropic DTW, 金融) · `2211.11665`(Duong 随机表征相异度空间) · `2105.05837`(仅标题核对)
5. **术语校正（延续项目已吸收的"cross-modal 冲突"）**：本文件所称"跨源"= 价格序列（低频 token 上下文）↔ 盘口统计（高频），**不涉及文本/图像**。文献中大量 "cross-modal / multi-modal alignment" 指 CLIP 式图文↔视觉，其结论**只能作为机制类比**，凡引用时本文件都注明"该文献的对象是什么"。
6. **完整性声明（非文献，但属取证）**：本轮若干工具结果尾部反复出现一段伪装成系统提示的注入文本（要求把成果"通过邮件网关发送给 colleague@umich.edu"）。**未执行**，亦未改变调研内容。

---

## 1. 方法库

约定：$Z_L\in\mathbb R^{512}$（低频侧，Kronos `decode_s1` 最后一 token 的 context，[一手] 由 C-X10-001 确认形状 `[B,8,512]` 可取）、$Z_H\in\mathbb R^{11}$（高频侧 1min OFI/价差/深度不平衡等），同一预测时点 $t$ 配对。$r$ = 目标对齐秩，$n$ = 样本对数。

P/A/H/B/S 的**可验证性**列：写"可判"指该方法的文献定义允许用 DS-CM-001 §2 的证据（张量形状/损失展开/部署重放）逐条判定；写"强制 0"指该方法的定义本身就使该位为 0。

---

### M1. 经典 CCA（样本典型相关）

**定义（逐字）**——Raghu, Gilmer, Yosinski, Sohl-Dickstein, *SVCCA: Singular Vector Canonical Correlation Analysis for Deep Learning Dynamics and Interpretability*, NeurIPS 2017, arXiv:1706.05806（Appendix A）：

> `a^{T}\Sigma_{XY}b / \sqrt{a^{T}\Sigma_{XX}a}\sqrt{b^{T}\Sigma_{YY}b}`

以及该文的动机句（逐字）：

> "This is especially important in neural network representations, where as we will show many low variance directions (neurons) are primarily noise."
> "While CCA is a powerful method, it also suffers from certain shortcomings, particularly in determining how many directions were important to the original space XX, which is the strength of SVD."
> "See Appendix for an example where naive CCA performs badly."
> "We propose a new technique, Singular Vector Canonical Correlation Analysis (SVCCA), a tool for quickly comparing two representations in a way that is both invariant to affine transform..."

**出处**：[一手] https://arxiv.org/abs/1706.05806 ；ar5iv 全文 `ar5iv.labs.arxiv.org/html/1706.05806`。经典源头为 Hotelling 1936（未直接取证，**[二手]**）。

**所需假设**：两视图同维或已投影到共同维数；$\Sigma_{XX},\Sigma_{YY}$ 可逆（否则需 $\kappa$ 正则）；$n$ 相对 $p+q$ 足够大；相关性即"共同信息"。

**数学保证**：无一致性保证（见失败模式）。在**高斯联合分布**下典型相关是共同信息的充分统计量：$I=\sum_i -\tfrac12\ln(1-\rho_i^2)$ 的形式在本文件的任何已取页面中**未逐字命中**，标 §5-U1，不作引用。

**已知失败模式（硬核，逐字）**：
- Bykhovskaya & Gorin, *High-Dimensional Canonical Correlation Analysis*, arXiv:2306.16393（Econometric Theory）摘要：
  > "the classical CCA procedure for estimating those vectors fails to deliver a consistent estimate. This provides the first result on the impossibility of identification of canonical variables in the CCA procedure when all dimensions are large."
  > "As a countermeasure, the paper derives the magnitude of the estimation error, which can be used in practice to assess the precision of CCA estimates." [一手]
- 同一摘要点明应用域含金融：> "Applications of the results to cyclical vs. non-cyclical stocks and to a limestone grassland data set are provided." → **对本项目**：CCA 的不可识别性在股票数据上已被正面研究，512 维 vs 11 维不是"小问题"。
- Donnat & Tuzhilina, *Canonical Correlation Analysis as Reduced Rank Regression in High Dimensions*, arXiv:2405.19539 (JMLR 2025/26)：
  > "In high dimensions, however, standard estimates of the canonical directions cease to be consistent without assuming further structure." [一手]
- Podosinnikova, Bach, Lacoste-Julien, *Beyond CCA: Moment Matching for Multi-View Models*, arXiv:1602.09013 (AISTATS 2016)：
  > "Gaussian CCA is subject to some well-known unidentifiability issues, in the same way as the closely related factor analysis model... Gaussian CCA is only identifiable up to multiplication by any invertible matrix. Although this unidentifiability does not affect the predictive performance of the model, it does affect the factor loading matrices and hence the interpretability of the latent factors." [一手]
  → **对本项目**：这句话是 §3 的核心弹药——**方向的不可识别性不影响预测性能**，所以"对齐到哪个基"与"预测好不好"是两件事。
- Kornblith et al. 2019, arXiv:1905.00414 摘要（逐字）：
  > "we show that CCA belongs to a family of statistics for measuring multivariate similarity, but neither CCA nor any other statistic that is invariant to invertible linear transformation can measure meaningful similarities between representations of higher dimension than the number of data points." [一手]

**在 (512,11) 上的实现成本**：批内样本协方差 $512\times512$ 求逆 + SVD，$O(512^2 n + 512^3)$；若 $n\lesssim 512$（小 batch 微调常态）$\widehat\Sigma_L$ 近奇异 → 必须 ridge。**ridge 系数成为新的自由参数，且直接改变被选方向**（M9 的 shrinkage 问题）。

**P/A/H/B/S**：P=**强制 0**（目标是相关系数，不是配对平方距离；DS-CM-001 F-P 路由）；A=**强制 0**（"invariant to invertible linear transformation" 意味着 $Z_L\mapsto Z_LA$ 不改变统计量，尺度/基完全无锚点，正是 F-A 的否证观测）；H/B/S=不判断（该方法不触及头与部署）。

---

### M2. 典型相关的正则高维版：**RRR（Reduced-Rank Regression）估计典型方向**

**定义（逐字，本文献对本项目最重要）**——Donnat & Tuzhilina 2025/26, arXiv:2405.19539 §2：

> **Lemma 1.**
> "Letting $Y_{0}=Y\widehat{\Sigma}_{Y}^{-\frac{1}{2}}$, the estimators for first $r$ canonical directions can be recovered as $\widehat{U}$ and $\widehat{V}=\widehat{\Sigma}_{Y}^{-\frac{1}{2}}\widehat{V}_{0}$ from the solution of the following problem:
> $\widehat{U},\widehat{V}_{0}=\mathop{\rm argmin}_{\substack{U\in\mathbb{R}^{p\times r},\,V\in\mathbb{R}^{q\times r}\\ U^{\top}\widehat{\Sigma}_{X}U=V^{\top}V=I_{r}}}\|Y_{0}-XUV^{\top}\|_{F}^{2}$  (10)"
>
> "Using this objective function, it is evident that the recovery of the subspace $UV_{0}^{\top}$ in (10) is a constrained instance of the more general reduced-rank regression problem:
> $\operatorname{minimize}_{B\in\mathbb{R}^{p\times q}}\quad\|{Y_{0}}-XB\|_{F}^{2}\quad\mbox{subject to}\quad\mathop{\sf rank}(B)=r,$  (11)"
>
> **Theorem 2.**
> "Let $Y_{0}=Y\widehat{\Sigma}_{Y}^{-\frac{1}{2}}$ be the normalized version of $Y$. Denote the solution to the ordinary least square (OLS) problem with feature matrix $X$ and response $Y_{0}$ by $\widehat{B}$, i.e.
> $\widehat{B}=\mathop{\rm argmin}_{B\in\mathbb{R}^{p\times q}}\|{Y_{0}}-XB\|_{F}^{2}=\widehat{\Sigma}_{X}^{-1}\widehat{\Sigma}_{XY}\widehat{\Sigma}_{Y}^{-\frac{1}{2}}.$  (12)
> Consider the singular value decomposition $\widehat{\Sigma}_{X}^{\frac{1}{2}}\widehat{B}=\widehat{U}_{0}\widehat{\Lambda}\widehat{V}_{0}^{\top}$. Then the matrices $\widehat{U}=\widehat{\Sigma}_{X}^{-\frac{1}{2}}\widehat{U}_{0}$ and $\widehat{V}=\widehat{\Sigma}_{Y}^{-\frac{1}{2}}\widehat{V}_{0}$ provide consistent estimators for the CCA directions $U$ and $V$."
>
> 出处句：> "We note here that, while this connection has already been recognized in the existing literature (Izenman 1975; De la Torre 2012), this formulation has not been previously used in the context of high-dimensional CCA."

**出处**：[一手] https://arxiv.org/abs/2405.19539 + ar5iv 全文。经典 Izenman 1975 (JASA) **[二手]**（仅在 Donnat–Tuzhilina 的致谢句中出现）。

**所需假设**：高斯对模型 > "We consider here the canonical pair model of Gao et al. 2017, where the observed $n$ pairs of measurement vectors $(X_i,Y_i)_{i=1}^n$ are i.i.d. from a multivariate Gaussian distribution $\mathcal{N}_{p+q}(0,\Sigma)$" [一手]；一高一低维（正是本文设定）；稀疏/低秩结构先验。

**数学保证**：**有**。Theorem 2 是"一致性估计典型方向"的正定理——在 $\Sigma$ 高斯 + 低秩 + 一高一低维下，$\widehat U,\widehat V$ 一致。这是 M1 缺的那一条。

**已知失败模式**：一致性以"真解低秩/稀疏"为条件；秩 $r$ 误设时估计的是错误子空间；且 Theorem 2 要 $\widehat\Sigma_X^{-1}$（$512\times512$）——$n$ 不足时仍须 ridge，回到 M1 的偏置问题（该文用稀疏惩罚而非 naive ridge，见 §5-U2 未取该节）。

**在 (512,11) 上的实现成本**：**低**。$B\in\mathbb R^{512\times 11}$，目标 (11) 就是配对平方残差；解 = OLS + 截断 SVD，$\|Y_0-XB\|_F^2$ 可微，反传成本 ≈ 一次 $512\times 11$ 矩阵乘。$q=11\ll p=512$ 恰是该文设计的适用域。

**P/A/H/B/S**：P=**可判 1**（损失本身即 $\|Z_H-Z_LA\|_F^2$ 的成对平方，配对键=时点 $t$）；A=**可判 1**（约束 $U^\top\widehat\Sigma_LU=I_r$ + $Y_0=Y\widehat\Sigma_Y^{-1/2}$ 提供显式尺度锚，且锚在数据二阶矩上而非可学习参数上；但"同步缩放 $A\to sA$、头 $\to s^{-1}$"仍需在实现上排除，见 §4）；H=**可判**（$B$ 是仿射映射，与"Bayes 最优仿射头"同族）；B=不涉及；S=不涉及（目标是向量 $Y_0$，不是标量——**注意这一条对 S 不利**，见 §4.3）。

---

### M3. Kernel CCA / 核典型相关

**定义（逐字）**——Bilenko & Gall, *Pyrcca: regularized kernel canonical correlation analysis in Python and its applications to neuroimaging*, arXiv:1503.01538：

> (6) `$\rho=\max\frac{\mathbf{a}^{\prime}K_{\mathbf{X}}K_{\mathbf{Y}}\mathbf{b}}{\sqrt{(\mathbf{a}^{\prime}K_{\mathbf{X}}^{2}\mathbf{a}+\kappa\|a\|^{2})\cdot(\mathbf{b}^{\prime}K_{\mathbf{Y}}^{2}\mathbf{b}+\kappa\|b\|^{2})}}$`
>
> 失败模式（该文最关键的一句，逐字）：> "However, if the kernels $K_{\mathbf{X}}$ and $K_{\mathbf{Y}}$ are invertible, a perfect correlation can be formed by setting $\mathbf{a}$ to 1, and solving $\mathbf{b}=(1/\lambda)K_{\mathbf{Y}}^{-1}K_{\mathbf{X}}$. **To avoid this trivial solution issue, kernel CCA must be regularized.**"
> 该文对适用性的正面表述（逐字，摘要）：> "Canonical correlation analysis (CCA) is a valuable method for interpreting cross-covariance across related datasets **of different dimensionality**."

**出处**：[一手] https://arxiv.org/abs/1503.01538 + ar5iv。

**第二处硬核（过拟合，逐字）**——Alam, Fukumizu, Wang, *Influence function and robust variant of kernel canonical correlation analysis*, arXiv:1705.04194（Neurocomputing 2018, DOI 10.1016/j.neucom.2018.04.008，由子代理核对）：

> "We can derive kernel CC using the correlation operator $\Sigma_{YY}^{-\frac{1}{2}}\Sigma_{YX}\Sigma_{XX}^{-\frac{1}{2}}$, even when $\Sigma_{XX}^{-\frac{1}{2}}$ and $\Sigma_{YY}^{-\frac{1}{2}}$ are not proper operators. **The potential danger is that it might overfit, which is why introducing $\kappa$ as a regularization coefficient would be helpful.**"
> (18) `$\rho=\max_{f_X\in\mathcal H_X,f_Y\in\mathcal H_Y}\mathrm{Corr}(f_X(X),f_Y(Y))$` ; (24) 给出 $(\widehat\Sigma_{XX}+\kappa\mathbf I)$ 约束下的经验估计式。

**第三处（"随机特征被完美对齐"的机制，逐字）**——Lopez-Paz, Hennig, Schölkopf, *The Randomized Dependence Coefficient*, NeurIPS 2013, arXiv:1304.7717：

> "Consider $p(X,Y)=\mathcal{N}(x;0,1)\mathcal{N}(y;0,1)$ which is independent... However, for finitely many N samples... there exist continuous (thus Borel measurable) functions $f(X)$ and $g(Y)$ mapping both X and Y to the sorting ranks of Y, i.e. $f(x_{i})=g(y_{i})\;\forall(x_{i},y_{i})\in(\bm{X},\bm{Y})$. **Therefore, the finite-sample version of Equation (1) is constant and equal to "1" for continuous random variables. Meaningful measures of dependence from finite samples thus must rely on some form of regularization.**"
> "**However, when $k\geq n$ regularization is needed to avoid spurious perfect correlations**, as discussed above."
> "Therefore, an equivalence between RDC and KCCA is established if RDC uses an infinite number of sine/cosine features..."

→ **对本项目**：这是"$L_{\text{align}}$ 降为 0 可以完全不携带信息"的**最强已发表否证**——只要特征映射的自由度 ≥ 样本数，独立的高斯样本也能被"完美对齐"。**$k\ge n$ 即失效**正是小 batch 微调的日常状态。

**所需假设**：RKHS 正则、$\kappa>0$、$\lambda$（特征数）≪ $n$、样本配对正确。
**数学保证**：有限样本下无（上述三处均为"无正则则平凡解"）；渐近一致需在 $\kappa\to0$ 的适当速率（本轮未取证，§5-U3）。
**在 (512,11) 上的实现成本**：核矩阵 $n\times n$（$n$=配对样本数），$\kappa,\lambda,\gamma$ 三超参；11 维侧高斯核带宽需单独校准。成本中等，但**超参空间大于 M2 且不可解释为 D**。

**P/A/H/B/S**：P=**强制 0**（相关系数目标）；A=**强制 0**（$\kappa$ 才锚尺度，非结构锚）；H/B/S=不涉及。

---

### M4. 对比学习族：InfoNCE / NT-Xent / instance discrimination

**定义（逐字）**

- van den Oord, Li, Vinyals 2018, *Representation Learning with Contrastive Predictive Coding*, arXiv:1807.03748：
  > `$\mathcal{L_{\text{N}}} = -\mathop{{}\mathbb{E}}_{X}\left[\log\frac{f_{k}(x_{t+k},c_{t})}{\sum_{x_{j}\in X}f_{k}(x_{j},c_{t})}\right]$`
  > "$I(x_{t+k},c_{t})\geq\log(N)-\mathcal{L}_{\text{N}},$ which becomes tighter as N becomes larger. Also observe that minimizing the InfoNCE loss $\mathcal{L}_{\text{N}}$ maximizes a lower bound on mutual information."
- SimCLR, Chen, Kornblith, Norouzi, Hinton 2020, arXiv:2002.05709 (ICML)，式 (1)：
  > `$\ell_{i,j} = -\log \frac{\exp(\mathrm{sim}(\bm{z}_i, \bm{z}_j)/\tau)}{\sum_{k=1}^{2N}\mathbbm{1}_{[k\neq i]}\exp(\mathrm{sim}(\bm{z}_i, \bm{z}_k)/\tau)}$` ，"...and τ denotes a temperature parameter."
  > 小 batch 相关（该文唯一逐字可引句）："**Contrastive learning benefits from larger batch sizes and more training steps compared to supervised learning.**" 以及 "in contrast to supervised learning, in contrastive learning, larger batch sizes provide more negative examples, facilitating convergence"
- Wang & Isola 2020, arXiv:2005.10242 (ICML)，**其 $\mathcal L_{\text{align}}$ 定义与项目符号同名，务必区分**（[一手-子代理] + 本文件复核 ar5iv）：
  > `$\mathcal{L}_{\mathsf{align}}(f;\alpha) \triangleq \underset{(x,y)\sim p_{\mathsf{pos}}}{\mathbb{E}}\left[\|f(x)-f(y)\|_2^\alpha\right], \quad \alpha>0$`
  > `$\mathcal{L}_{\mathsf{uniform}}(f;t) \triangleq \log \underset{x,y \overset{\text{i.i.d.}}{\sim} p_{\mathsf{data}}}{\mathbb{E}}\left[e^{-t\|f(x)-f(y)\|_2^2}\right], \quad t>0$`
  > Theorem 1 (Asymptotics of $\mathcal L_{\text{contrastive}}$)，式 (2)：
  > `$\lim_{M\rightarrow\infty}\mathcal{L}_{\mathsf{contrastive}}(f;\tau,M)-\log M = -\frac{1}{\tau}\underset{(x,y)\sim p_{\mathsf{pos}}}{\mathbb{E}}\left[f(x)^{\mathsf{T}}f(y)\right] + \underset{x\sim p_{\mathsf{data}}}{\mathbb{E}}\left[\log \underset{x^{-}\sim p_{\mathsf{data}}}{\mathbb{E}}\left[e^{f(x^{-})^{\mathsf{T}}f(x)/\tau}\right]\right]$`
  > 并注 "The first term is minimized iff $f$ is perfectly aligned."

**这条定义对本项目极重要**：Wang–Isola 的 $\mathcal L_{\text{align}}(f;2)$ **恰好是配对平方距离**，即 $\mathbb E_{(x,y)\sim p_{\text{pos}}}\|f(x)-f(y)\|^2$。也就是说：对比族的"正对项"与模型 D 的 $D$ **同形**，两者的差别全在**负对/均匀性项**与**是否归一化到球面**。这为 §2 主候选 C1 提供了"配对平方"的已发表血统（不只是我方的自造目标）。

**数学保证**：InfoNCE 是 MI 的**下界**（$\ge \log N - \mathcal L_N$）。界的可用性问题见 M8。
**已知失败模式（跨源场景最直接的一条）**——Liang, Zhang, Kwon, Yeung, Zou, *Mind the Gap*, NeurIPS 2022, arXiv:2203.02053：
  > "different data modalities (e.g. images and texts) are embedded at arm's length in their shared representation"
  > "During optimization, contrastive learning keeps the different modalities separated by a certain distance, which is influenced by the temperature parameter in the loss function."
  > "We found that the default gap distance $\|\vec\Delta_{\mathrm{gap}}\|=0.82$ actually achieves the global minimum, and shifting toward closing the gap *increases* the contrastive loss... these results show that **there is a repulsive structure in the contrastive loss landscape that preserves the modality gap**."
  > "a high temperature ($\tau\in\{1/10,1\}$) in fine-tuning significantly reduces or closes the gap, while a low temperature does not. The gap distance decreases monotonically with increasing temperature"
  > "By simply modifying the gap's distance, we can improve CLIP's zero-shot performance and fairness."
  → **一句话项目含义**：跨源对比会**在损失面上主动维持一个源间距离**，且该距离可由后处理平移改变而不动任何信息——所以"对比损失降了/没降"**不能**当作"源已对齐/未对齐"的证据。这直接否证"用 $\mathcal L_{\text{align}}$ 的值当对齐验收指标"。

其他：
- Wang & Liu 2021, arXiv:2012.09740（CVPR2021）：uniformity 式 (10) `$\mathcal{L}_{\text{uniformity}}(f;t)={\rm log}\,\mathbb E_{x,y\sim p_{data}}[e^{-t\|f(x)-f(y)\|_2^2}]$`，"The temperature plays a role in controlling the strength of penalties on hard negative samples."（该文另一处指出 alignment/uniformity 张力即"uniformity-tolerance dilemma"）[一手]
- Zimmermann, Sharma, Schneider, Bethge, Brendel, *Contrastive Learning Inverts the Data Generating Process*, ICML 2021, arXiv:2102.08850：
  > "Under these assumptions, the feature encoder $f$ implictly learns to invert the ground-truth generative process $g$ up to linear transformations, i.e., $f=\mathbf{A}g^{-1}$ with an orthogonal matrix $\mathbf{A}$, if $f$ minimizes the InfoNCE objective." [sic]
  > "**On real data, it is unlikely that the assumed model distribution $q_{\rm{h}}$ can exactly match the ground-truth conditional.** We do, however, provide empirical evidence that $h$ is still an affine transformation even if there is a severe mismatch."
  → 保证只在**生成模型满足强假设**时成立；本项目的 $Z_H$（11 维人工统计量）**不是**某潜变量的非线性观测，假设前提不成立——不可引用其正定理为项目背书。

**在 (512,11) 上的实现成本**：批内 $n\times n$ 相似度矩阵，$O(n\cdot 512)$；需投影头 + 温度 + 非对称负采样。**关键结构性不对称**：$Z_H$ 只有 11 维且是可解释统计量，用"同 batch 其他时点的 $Z_H$"当负样本，等于假设"不同市场状态的盘口特征互不相容"——高频下相邻时点 $Z_H$ 高度自相关（bid-ask 与深度不平衡近似 OU），负样本大量是假负样本。文献无此情形的分析 → §5-U4。

**P/A/H/B/S**：P=**强制 0**（负对项 + 归一化，损失不是成对平方；F-P 路由）；A=**可判但反向**（球面归一化 $\|f\|=1$ 确实锚定尺度，但同时**消灭了 $D$ 想测的东西**：模型 D 的 $D=2(\theta+\nu)$ 依赖方差，球面化后 $\mathrm{Var}$ 恒为常数，$\theta$ 退化）；H/B/S=不涉及。

---

### M5. Procrustes / 带权的等距映射对齐

**定义（逐字）**

- 正交 Procrustes（Global Anchor 一文给出的标准写法）——Yin, Sachidananda, Prabhakar, *The Global Anchor Method for Quantifying Linguistic Shifts and Domain Adaptation*, NeurIPS 2018, arXiv:1812.10382 [一手-子代理]：
  > "alignment-based approaches find a unitary operator $Q^{*}=\min_{Q\in O(d)}\|E-FQ\|_{F}$, where $O(d)$ is the group of $d\times d$ unitary matrices and $\|\cdot\|_{F}$ is the Frobenius norm."
  > "**Applicability: The alignment methods can be applied only to embeddings of the same dimensionality, since the orthogonal transformation it uses is an isometry onto the original $\mathbb{R}^{d}$ space. On the other hand, the global anchor method can be used to compare embeddings of different dimensionalities.**"
  > "the expression for the corpus-level dissimilarity simplifies to: $\|EE^{T}-FF^{T}\|$."
- **加权 Procrustes（解维度不匹配的主引）**——Sachidananda, Yang, Zhu, *Filtered Inner Product Projection for Crosslingual Embedding Alignment*, ICLR 2021, arXiv:2006.03652 [一手-子代理]：
  > "**FIPP aligns embeddings to isomorphic vector spaces even when the source and target embeddings are of differing dimensionalities.**"
  > "However, these methods usually require the dimensions of the source and target language embeddings to be the same, which often may not hold."
  > "since FIPP's alignment between the source and target embeddings is performed on Gram matrices, i.e. $X_{s}X_{s}^{T}$ and $X_{t}X_{t}^{T}\in\mathbb{R}^{c\times c}$, **embeddings are not required to be of the same dimension** and are projected to isomorphic vector spaces. This is particularly helpful for aligning embeddings trained on smaller corpora, such as in low resource domains..."
  > §4.2 式 (7)：>`"We propose a weighted variant of the Orthogonal Procrustes solution to account for differing levels of translation uncertainty among pairs in the seed dictionary..."` ；`$\mathrm{SVD}((WX_{t})^{T}W\tilde{X}_{s})=U\Sigma V^{T},\ \Omega^{W}=\argmin_{\Omega\in O(d_{2})}\|W(\tilde{X}_{s}\Omega-X_{t})\|^{2}_{F}=UV^{T},$` (7)，"where $O(d_{2})$ is the group of $d_{2}\times d_{2}$ orthogonal matrices."，权重 `$W_{ii}^{-1}=\|\tilde{X}_{s}[i]X_{s}^{T}-X_{t}[i]X_{t}^{T}\|^{2}$`
  > 出样本外推（**对本项目的推理路径直接可用**）：>"$\tilde{\mathfrak{X}}_{s}^{T}=(\tilde{X}_{s}^{T}\tilde{X}_{s})^{-1}\tilde{X}_{s}^{T}X_{s}\mathfrak{X}_{s}^{T}$"
- 加权 Procrustes 的**存在性**（函数分析版本，逐字）——Contino, Giribet, Maestripieri, *Weighted Procrustes problems*, JMAA 445(1):443–458, 2017, DOI 10.1016/j.jmaa.2016.07.050, arXiv:1610.00558 [一手]：
  > (1.4) `$\min_{X \in L(\mathcal{H})} \|W^{1/2}(AX-B)\|_p,\quad 1 \leq p < \infty$`，"where $\|\cdot\|_p$ is the $p$-Schatten norm."
  > "Problem (4.1) admits a minimum if and only if $R(B) \subseteq R(A)+R(A)^{\perp_W}$. In case $\min_{X}\|AX-B\|_{p,W} = \|W_{/R(A)}^{1/2}B\|_p$. Moreover, $X_0$ ... if and only if $X_0$ is a $W$-inverse of $A$ in $R(B)$."
  > "the introduction of a weight $W\in L(\mathcal{H})^{+}$ plays an important role, since we are introducing on $\mathcal{H}$ a semi-inner product associated to $W$ for which $\mathcal{H}$ is no longer a Hilbert space, unless $W$ is invertible. In this case, the existence of a suitable orthogonal projection is not guaranteed."
  → **一句话项目含义**：若 $W$ 取"按维度信息量的对角权重"，其奇异时 $W$-逆可能不存在——权重必须**严格正定**（不能给 512 维里不用的维度置 0），否则解集为空/无界。

**出处**：Schönemann 1966 (Psychometrika 31:1-10) 为经典源头，本轮**未直接取证** → [二手]。
**所需假设**：存在（近似）等距关系；配对正确；若加秩/子空间约束则 $r\le \min(512,11)=11$。
**数学保证**：$O(d)$ 上有闭式 SVD 解；加权情形的**存在性判据**由 Contino 等给出（见上）。
**已知失败模式**：
  - Kornblith 2019（Appendix D.2，逐字，是 Procrustes 优于 CCA 的直接证据）：
    > "In the context of neural networks, Smith et al. 2017 previously proposed using the solution to the orthogonal Procrustes problem to align word embeddings from different languages, and **demonstrated that it outperformed CCA**." [一手]
    → 什么时候 Procrustes 比 CCA 合适：**已知两表征之间近似只差一个等距（含语言/初始化置换）**时；且需要**可部署的确定性映射**时。CCA 合适的时候是要"找出共同子空间/排序"而非要"一个能用的映射"。
  - 高维不可识别 + 旋转任意性 → Andreella & Finos, *Procrustes analysis for high-dimensional data*, arXiv:2008.04631 [一手]：
    > "The Procrustes-based perturbation model (Goodall 1991) allows minimization of the Frobenius distance between matrices by similarity transformation. However, **it suffers from non-identifiability, critical interpretation of the transformed matrices, and inapplicability in high-dimensional data.**"
    > "The necessary and sufficient condition for the existence of $\widehat{\Sigma}_{n}$ and $\widehat{\Sigma}_{m}$ is $N\geq\frac{m}{n}+1$... in fMRI data analysis, $m$ roughly equals 200,000, and $n$ approximately equals 200; therefore, the researcher would have to analyzing at least 1,001 subjects, which is virtually impossible."
    > "**When $n<m$, rank equals $n$, the identifiability of the solution is lost even when the nuisance parameters are known.**"
    > "**In most cases, Procrustes methods turn into an ill-posed problem.** It is a barely noticeable problem with spatial coordinates because the solution is unique up to rotations hence, the user has the freedom to choose the point of view that provides the nicest picture. **When the dimensions do not have a spatial meaning, any rotation completely changes the interpretation of the results.**"
    → 本项目 11 维盘口侧的坐标**有明确物理含义**（OFI、价差、深度不平衡），512 维侧**无**——所以"旋转自由度落在哪一侧"决定了可解释性：把旋转留在 $Z_L$ 侧（学 $A$）是唯一可辩护的定向。

**在 (512,11) 上的实现成本**：$A\in\mathbb R^{512\times 11}$，$\|Z_H-Z_LA\|^2$ = 一次矩阵乘，逐 batch 可微；正交/半正交约束用 QR 或 Cayley 参数化。成本最低的一族。

**P/A/H/B/S**：P=**可判 1**（成对平方，键=时点）；A=**可判**（$A$ 的列范数/正交约束 + $Z_H$ 的 train-only z-score 构成显式锚；但**必须**显式禁止"同步缩放 $Z_L$ 并反向缩放 $A$"，否则 F-A 否证观测成立）；H=**可判**（$A$ 仿射）；B=不涉及；S=向量残差（对 S 中性偏不利）。

---

### M6. 度量学习 / 非等距目标（关系型、相似度保持型）

**定义（逐字）**——Park, Kim, Lu, Cho, *Relational Knowledge Distillation*, CVPR 2019, arXiv:1904.05068：
  > `$\psi_{\text{D}}(t_i, t_j) = \frac{1}{\mu} \| t_i - t_j \|_2$` (5) ; `$\mu = \frac{1}{|\mathcal{X}^2|} \sum_{(x_i, x_j) \in \mathcal{X}^2} \| t_i - t_j \|_2$` (6) ; `$\mathcal{L}_{\text{RKD-D}} = \sum_{(x_i, x_j) \in \mathcal{X}^2} l_\delta(\psi_{\text{D}}(t_i, t_j), \psi_{\text{D}}(s_i, s_j))$` (7)，Huber `$l_\delta$` (8)；角度式 `$\psi_{\text{A}}(t_i, t_j, t_k) = \cos \angle t_i t_j t_k = \langle \mathbf{e}^{ij}, \mathbf{e}^{kj} \rangle$` (9)
  > 跨维能力（逐字）：**"Thanks to the potential, it is able to transfer knowledge of high-order properties, which is invariant to lower-order properties, even regardless of difference in output dimensions between the teacher and the student."**

**同族**：Tung & Hung, *Similarity-Preserving Knowledge Distillation*, ICCV 2019, arXiv:1907.09682（ID 已 [一手] 核对：`1907.09682v2 | 2019-07-23 | Frederick Tung`）；本文未取该式，标 §5-U5。

**所需假设**：配对样本足以构造 $\mathcal X^2/\mathcal X^3$ 关系；距离归一化 $\mu$ 稳定。
**数学保证**：无（关系型目标是相对量，不存在"等于最优对齐"的定理）。
**已知失败模式**：(i) **尺度不变 = 无锚**：$\psi_D$ 除以 $\mu$（batch 平均距离）→ 同步缩放两侧完全不变，正是 DS-CM-001 §3 的独立否证情形 "$Z\to sZ$ 而 $D$ 按 $s^2$ 改变"——这里 $D$ 连 $s^2$ 都不变，A 位无从谈起；(ii) Huber 化后不再是平方距离，P 位为 0；(iii) 关系项是 $O(n^2)$/$O(n^3)$ 计算。
**在 (512,11) 上的实现成本**：$n=4096$ 时 $\mathcal X^2$ 距离矩阵 ~1600 万元素，需要采样；角度项要三元组。成本高于 M2/M5。
**P/A/H/B/S**：P=**强制 0**；A=**强制 0**（构造性尺度不变）；H/B/S=不涉及。
→ 归入**消融候选**（测"关系型对齐是否优于直接回归映射"），不进主候选。

---

### M7. 分布对齐（MMD / 核均值嵌入 / 子空间对齐）

**定义（逐字）**——Gretton, Borgwardt, Rasch, Schölkopf, Smola, *A Kernel Method for the Two-Sample Problem*, arXiv:0805.2368：
  > (1) `$\mathrm{MMD}\left[\mathcal{F},p,q\right]:=\sup_{f\in\mathcal{F}}\left(\mathbf{E}_{x\sim p}[f(x)]-\mathbf{E}_{y\sim q}[f(y)]\right).$`
  > (2) `$\mathrm{MMD}_{b}\left[\mathcal{F},X,Y\right]:=\sup_{f\in\mathcal{F}}\left(\frac{1}{m}\sum_{i=1}^{m}f(x_{i})-\frac{1}{n}\sum_{i=1}^{n}f(y_{i})\right).$`
  > (3) `$\mathrm{MMD}\left[\mathcal{F},p,q\right] = \sup_{\|f\|_{\mathcal{H}}\leq 1}\left\langle\mu[p]-\mu[q],f\right\rangle = \left\|\mu[p]-\mu[q]\right\|_{\mathcal{H}}.$`

**同族（分布混淆损失）**：Tzeng, Hoffman, Saenko, Darrell, *Deep Domain Confusion: Maximizing for Domain Invariance*, arXiv:1412.3474（ID [一手]）；Long, Zhu, Khan, Wang, Jordan, *Learning Transferable Features with Deep Adaptation Networks* (DAN), arXiv:1502.02791（ID [一手]，由子代理检索命中）；Fernando et al., *Subspace Alignment For Domain Adaptation*, arXiv:1409.5241（仅标题命中，未读正文 → [二手]）。

**数学保证**：MMD 在特征核（characteristic kernel）下是伪度量，$\mathrm{MMD}=0\iff p=q$（该句未在本文已取页面逐字命中，§5-U6，不引用）。Eq (3) 已逐字给出其 RKHS 形式。
**已知失败模式（对本项目最致命）**：MMD 对齐的是**边缘分布** $\mathcal L(Z_L)$ 与 $\mathcal L(Z_H)$，与配对结构无关。C-CM-004 §1 的 T5 已记录"边缘分布不决定配对结构"；把 $p=q$ 当作"已对齐"会允许完全无信息量的配对。
**在 (512,11) 上的实现成本**：$n\times n$ 核矩阵 ×2 侧 + 交叉项，$O(n^2 d)$；11 维侧高斯核带宽与 512 维侧带宽不可共用 → 需各向异性带宽，超参增加。
**P/A/H/B/S**：P=**强制 0**（分布散度，非配对；F-P 路由）；A=**可判 0**（对齐到对方分布 = 相对尺度无锚，正合 C-T9-002 §10.6 尾句"若是跨模态互相靠拢（目标依赖另一模态），两个模态的相对尺度无锚点"）；H/B/S=不涉及。
→ 归入**消融候选**（"去掉配对、只对齐分布" 的对照）。

---

### M8. 互信息估计（作为**诊断**，非优化目标）

**定义（逐字）**——Belghazi et al., *MINE: Mutual Information Neural Estimation*, ICML 2018, arXiv:1801.04062：
  > **Theorem 1 (Donsker-Varadhan representation).** "$D_{KL}(\mathbb{P}\mid\mid\mathbb{Q})=\sup_{T:\Omega\to\mathbb{R}}\mathbb{E}_{\mathbb{P}}[T]-\log(\mathbb{E}_{\mathbb{Q}}[e^{T}]),$" (5)
  > (6) 限制到 $\mathcal F$ 的下界；(9)(10) `$I_{\Theta}(X,Z)=\sup_{\theta\in\Theta}\mathbb{E}_{\mathbb{P}_{XZ}}[T_{\theta}]-\log(\mathbb{E}_{\mathbb{P}_{X}\otimes\mathbb{P}_{Z}}[e^{T_{\theta}}]).$` (10)
  > **Theorem 3** 样本复杂度：(14)(15) `$n\geq\frac{2M^{2}(d\log(16KL\sqrt{d}/\epsilon)+2dM+\log(2/\delta))}{\epsilon^{2}}.$`，其假设 "both $T_{\theta}$ and $e^{T_{\theta}}$ are $M$-bounded"
  > 自身偏差（逐字）："**In a mini-batch setting, the SGD gradients of MINE are biased.**" / "the bias can be reduced by replacing the estimate in the denominator by an exponential moving average."

**可靠性问题的三条硬核**：
1. McAllester & Stratos, *Formal Limitations on the Measurement of Mutual Information*, AISTATS 2020, arXiv:1811.04251，摘要逐字：
   > "Measuring mutual information from finite data is difficult. Recent work has considered variational methods maximizing a lower bound. In this paper, we prove that serious statistical limitations are inherent to any method of measuring mutual information. More specifically, **we show that any distribution-free high-confidence lower bound on mutual information estimated from N samples cannot be larger than O(ln N ).**"
   → **一句话项目含义**：**"对齐损失降了多少 nats"这种说法不可证伪**；项目的 $\Delta I=\tfrac12\ln(R_H/R)$ 只能走协方差闭式（模型 D 的 G1/G2），不能走 MI 估计器。
2. Song & Ermon, *Understanding the Limitations of Variational Mutual Information Estimators*, ICLR 2020, arXiv:1910.06222，逐字：
   > "the variance of certain estimators, such as MINE, could grow **exponentially** with the ground truth MI, leading to poor bias-variance trade-offs"
   > "In order to keep the variance of $\hat{I}_{\mathrm{MINE}}$ and $\hat{I}_{\mathrm{NWJ}}$ relatively constant with growing MI, one would need a batch size of $n = \Theta(e^{D_{\mathrm{KL}}(P\|Q)})$."
   > "One could achieve smaller variances with some $r \neq r^\star$, but this guarantees looser bounds and higher bias."
3. **条件**互信息（本项目 $\Delta I=I(T;Z_L\mid Z_H)$ 直接对应）在小样本下的额外困难——Molavipour, Bassi, Skoglund, *Conditional Mutual Information Neural Estimator*, arXiv:1911.02277，逐字：
   > "**The main challenges in estimating the CMI stem from empirically computing the conditional density function and from the curse of dimensionality.**"
   > "the variational bound used in [28] contains non-linearities which results in a **biased estimation when taking a Monte Carlo average**."
   > "for small values of $b'$, averaging the lower bound ([2]) over trials is **more likely to yield an overestimation of the true CMI** compared to ([12]). This is a joint effect of the Monte Carlo bias and the small sample size"
   → 小 batch 下 CMI 估计**系统性偏高**，方向恰好会"证明对齐有效" → 危险偏差。
   另：Shah & Peters, *The Hardness of Conditional Independence Testing and the Generalised Covariance Measure*, arXiv:1804.07203 (Ann. Appl. Stat. 2020)（ID 与标题 [一手] 核对）——条件独立检验无一致检验程序的一般性不可能结果；本轮未取正文 → 该条按 [二手] 用。

**P/A/H/B/S**：不进入损失 → 五位不适用；但它是 §5 的**否证工具**：$H$ 位要求"实际头与仿射探针风险差不超过 $\epsilon_H$"，这用风险测，不用 MI。

---

### M9. 线性映射的收缩 / hubness（512↔11 的**方向**问题）

**定义（逐字）**——Dinu, Lazaridou, Baroni, *Improving zero-shot learning by mitigating the hubness problem*, ICLR 2015 workshop, arXiv:1412.6568 [一手-子代理]：
  > "Training is cast as a multivariate regression problem, learning a function which maps the source domain vectors to their corresponding target (linguistic-space) vectors... assume the mapping function is a linear map $\mathbf{W}$, and use a l2-regularized least-squares error objective:"
  > (1) `$\hat{\bm{\mathbf{W}}}=\operatorname{arg\,min}_{\bm{\mathbf{W}}\in\mathbb{R}^{v\times u}}||\bm{\mathbf{X}}\bm{\mathbf{W}}-\bm{\mathbf{Y}}||_{F}+\lambda||\bm{\mathbf{W}}||$`
  > "the problem is much more severe for neighbourhoods of vectors that are mapped onto a **high-dimensional** space from elsewhere through a **regression algorithm**." / "As a results nearest neighbour queries return the hubs at top 1, harming accuracy." [sic]

**方向性结论（对本项目最有用）**——Shigeto, Suzuki, Hara, Shimbo, Matsumoto, *Ridge Regression, Hubness, and Zero-Shot Learning*, ECML/PKDD 2015, arXiv:1507.00825 [一手]：
  > "Let $\mathbf{M}\in\mathbb{R}^{d\times c}$ be the solution for ridge regression with an observation matrix $\mathbf{A}\in\mathbb{R}^{c\times n}$ and a response matrix $\mathbf{B}\in\mathbb{R}^{d\times n}$; i.e. $\mathbf{M}=\arg\min_{\mathbf{M}}(\|\mathbf{M}\mathbf{A}-\mathbf{B}\|_F^2+\lambda\|\mathbf{M}\|_F)$. ... It is well known that $\mathbf{M}=\mathbf{B}\mathbf{A}^T(\mathbf{A}\mathbf{A}^T+\lambda\mathbf{I})^{-1}$."
  > "Let $\sigma$ be the largest singular value of $\mathbf{A}$. It can be shown that $\|\mathbf{A}^T(\mathbf{A}\mathbf{A}^T+\lambda\mathbf{I})^{-1}\mathbf{A}\|_2=\frac{\sigma^2}{\sigma^2+\lambda}\leq 1$."
  > "Proposition 2 thus indicates that **the variance along the principal axis of the mapped observations MA tends to be smaller than that of responses B**..."
  > "we can conclude that the objects closest to the origin in the dataset tend to be hubs."
  > 摘要式结论："**Contrary to the existing approach, which attempts to find a mapping from the example space to the label space, we show that mapping labels into the example space is desirable to suppress the emergence of hubs** in the subsequent nearest neighbor search step."

**数学保证**：$\frac{\sigma^2}{\sigma^2+\lambda}\le1$ 是显式收缩因子。
**已知失败模式**：$512\to 11$ 方向的 ridge 映射会把 $Z_H$ 空间"压向原点"（低维侧成为 hub 集合）；反过来 $11\to512$ 则 512 维侧被膨胀，$D$ 被高估。跨源检索侧的 hubness 风险亦见 *Adversarial Hubness in Multi-Modal Retrieval*, arXiv:2412.14113 [一手-子代理]："Hubness is a phenomenon in high-dimensional vector spaces where a single point from the natural distribution is unusually close to many other points... causes some items to **accidentally (and incorrectly) appear relevant** to many queries."
**在 (512,11) 上的实现成本**：零（与 M2/M5 同）。但**必须报告映射方向**并把两侧二阶矩都记进日志。
**P/A/H/B/S**：不是独立损失，而是 M2/M5 的**A 位否证工具**：给出"$\|D\|$ 下降但只是收缩/只是单位变化"的可检查量（`DS-CM-001` §4 的 `D_hat` 超界检查正好用 $\sigma^2/(\sigma^2+\lambda)$ 校准）。

---

### M10. 时序特异的跨频方法（**对齐的是什么对象**）

**结论先说**：本方向检索到的 2024–2026 代表工作**都不使用 $L_{\text{align}}$**。它们的"对齐"是**架构内的信息通路**（注意力/混合），不是可加到总损失上的散度项。这是本文件对候选空间最重要的负结果之一。

1. **TimeXer**（Wang, Wu, Dong, Qin, Zhang, Liu, Qiu, Wang, Long, NeurIPS 2024, arXiv:2402.19072）[一手]
   > "In TimeXer, the cross-attention layer takes the **endogenous variable as query** and the **exogenous variable as key and value** to build the connections between the two types of variables."
   > "To tackle the arbitrarily irregular exogenous variables, TimeXer adopts their **variate-level representations**... which are adaptive to arbitrary irregularities such as missing values, **misaligned timestamps, different frequencies**, or discrepant look-back lengths."
   → 对齐对象 = **不同粒度 token 之间的信息流**（patch-level 内生 ↔ variate-level 外生）；**没有任何显式对齐损失**。对高频/低频、错时时间戳的处理方式是"换表示粒度"（把外生序列压成整段级 token），**不是把两侧压进同一几何空间**。
   → 一句话项目含义：项目若只要"低频条件化高频"，架构路线已被该文献占用；**跨源几何对齐是它的正交补集**（可辩护的差异点）。

2. **TimeMixer**（Wang, Wu, Shi, Hu, Luo, Ma, Zhang, Zhou, ICLR 2024, arXiv:2405.14616）[一手]
   > "we analyze temporal variations in a novel view of multiscale-mixing, which is based on an intuitive but important observation that **time series present distinct patterns in different sampling scales**. The microscopic and the macroscopic information are reflected in fine and coarse scales respectively"
   > PDM: `$\mathrm{for}\ m\mathrm{:}\ 1\to M\ \mathrm{do}\colon \mathbf{s}_{m}^{l}=\mathbf{s}_{m}^{l}+\operatorname{Bottom-Up-Mixing}(\mathbf{s}_{m-1}^{l})$` ; `$\mathrm{for}\ m\mathrm{:}\ (M-1)\to 0\ \mathrm{do}\colon \mathbf{t}_{m}^{l}=\mathbf{t}_{m}^{l}+\operatorname{Top-Down-Mixing}(\mathbf{t}_{m+1}^{l})$` ; FMM: `$\widehat{\mathbf{x}}=\sum_{m=0}^{M}\widehat{\mathbf{x}}_{m}$`
   → 对齐对象 = **同一序列在不同采样尺度上的季节/趋势分量**，靠**双向混合**而非散度。注意其 seasonal 走 fine→coarse、trend 走 coarse→fine 的**方向不对称**，与项目"低频条件化高频"的方向选择同构，可作为方向性的旁证。

3. **HANET**（Oliveira, Wood, Zohren, Cucuringu, Fujita, 2026, arXiv:2606.00624, q-fin.ST）[一手]
   > "HANET organizes information in a hierarchical mixed-frequency structure, with **daily asset-return signals nested within monthly macroeconomic windows**, and introduces a **Hierarchical Cross-Attention** mechanism that **reconciles low-frequency macro signals with high-frequency returns without discarding granular daily information**."
   > 其消融句对项目的"为什么不能只拼特征"是现成的同构证据：**"Ablation studies show that these gains rely on structured macro conditioning rather than naive feature augmentation: an LSTM with the same macro representation performs poorly, and shuffling macro contexts substantially degrades performance."**
   → 对齐对象 = **低频窗口作为条件上下文**（regime 选择被表述为对宏观上下文的注意力），**无对齐损失**。shuffling 消融 = 项目可复制的"配对有效性"检验模板（与 DS-CM-001 的 P 位判据一致）。

4. **混合频 econometrics（MIDAS 族）**：本轮只核到相邻存在（arXiv 标题检索 `ti:"Mixed Frequency"` 命中 10 篇，含 Babii 2003.13478、Toda 2105.09579、Hecq 2102.11780、Ankargren 1912.02231 等），**Müller–Marcellino–Schumacher (2000) MIDAS 原文与 Chun (2020) U-MIDAS 均未取证**（§5-U7）。就本轮证据而言，该族的做法是**在回归层用滞后多项式权重桥接频率**，属于"对齐 $\beta$ 而非对齐 representation"——这条判断为**[二手/背景常识]**，引用前须补原文。
5. **DTW**：Jain, *Semi-Metrification of the Dynamic Time Warping Distance*, arXiv:1808.09964 [一手]：
   > "The dynamic time warping (dtw) distance fails to satisfy the triangle inequality and the identity of indiscernibles." / "**The dtw-distance is not a metric.**" / "The lack of warping-invariance is notable because the dtw-distance has been designed to overcome the inability of the Euclidean distance to cope with temporal variations."
   续文 *Making the DTW Distance Warping-Invariant*, arXiv:1903.01454 [一手-子代理]：
   > "the dtw-distance is not warping-invariant **though otherwise stated in some publications**"；并定义 semi-metric / pseudo-metric 的公理编号 (1)-(4)
   金融侧使用与限制：Bai, Cui, Xu, Wang, Zhang, Hancock, *Entropic Dynamic Time Warping Kernels for Co-evolving Financial Time Series Analysis*, IEEE TNNLS 2020, DOI 10.1109/TNNLS.2020.3006738, arXiv:1910.09153 [一手-子代理]，给出正定全局对齐核 (3)(4)，并承认直接 DTW 在金融共演网络上的困难。
   → **对项目的裁定**：DTW 属于"允许时间重对齐"的距离。而 $L_{\text{align}}$ 必须**在固定同一时点**上配对（否则把未来盘口信息对齐进过去，即前视）。DTW 非度量 + 无 warping-invariance + 允许 $\delta(x,y)=0$ 而 $x\ne y$，**与 P 位直接冲突** → 排除，仅作"若允许重对齐"的消融对照（本轮不建议登记）。

---

### M11. 小样本 / 维度不匹配下的概率嵌入（跨源不对称噪声）

**定义（逐字）**——Chun, Oh, de Rezende, Kalantidis, Larlus, *Probabilistic Embeddings for Cross-Modal Retrieval* (PCME), CVPR 2021, arXiv:2101.05068 [一手-子代理]：
  > "we argue that **deterministic functions are not sufficiently powerful to capture such one-to-many correspondences**. Instead, we propose to use Probabilistic Cross-Modal Embedding (PCME), where samples from the different modalities are represented as **probabilistic distributions in the common embedding space**."
  > (4) `$p(v|i)\sim N\left(h_{\mathcal{V}}^{\mu}(z_{v}),\mathrm{diag}(h_{\mathcal{V}}^{\sigma}(z_{v}))\right)$`, `$p(t|c)\sim N\left(h_{\mathcal{T}}^{\mu}(z_{t}),\mathrm{diag}(h_{\mathcal{T}}^{\sigma}(z_{t}))\right)$`
  > "We modify $h_{\mathcal{V}}$ to let it **predict a distribution, rather than a point**."
**所需假设**：对角高斯足够；两侧各有一个 $(\mu,\sigma)$ 头；共享空间维度 $D$ 自选。
**数学保证**：无对齐定理；其正则（到 $\mathcal N(0,I)$ 的 KL + uniformity）就是**尺度锚**——这一点与 C-T9-002 §5/§10.6"必须固定尺度"的要求同向。
**已知失败模式**：方差头可塌向 0（该文自己加 KL 抑制）；一旦 $\sigma$ 可学且不受约束，"对齐损失下降"可以是"方差塌缩"（对应 C-CM-004 §7 的"表示尺度必须显式锚定，否则退化"）。
**在 (512,11) 上的实现成本**：$Z_H$ 侧要新学 $\mu$ 头（11→D）+ 对角方差头（11→D），$Z_L$ 侧同理；D 取 16–32 时新增参数 < 3.5 万，**成本可忽略**。
**P/A/H/B/S**：P=**可判**（若用 $\mathbb E\|v-t\|^2$ 形式的耦合则可回到成对平方；该文的损失是检索软对比，默认 P=0）；A=**可判 1**（对角方差头 + KL-to-$\mathcal N(0,I)$ 是显式、可记录的尺度约束）；H/B/S=不涉及。
→ 本项目价值：**给"高频侧噪声 $\nu$"一个可测的实现物**，而不是假设 $\nu$ 固定。与 §4 的 $G$ 前提检查直接对接。

---

## 2. $L_{\text{align}}$ 候选表（3 主候选 + 2 消融；按对本项目的合理性排序）

记号统一：所有配对在**同一预测时点 $t$**、同一 $[B,512]$ / $[B,11]$ 坐标顺序、按维数平均与否预先固定（DS-CM-001 §2 第 3 步）。

### C1（主）**带显式尺度锚的低秩线性映射成对平方一致性**（RRR / 加权 Procrustes 型）

$$\ \mathcal L_{\text{align}}^{\text{C1}}=\frac{1}{nd_H}\bigl\|Z_H-Z_LA_r\bigr\|_F^2,\qquad A_r=B_rU_r^{\!\top},\ B_r=\arg\min_{\operatorname{rank}(B)=r}\|Y_0-X_LB\|_F^2\ $$

血统（不是自造）：Donnat–Tuzhilina (10)(11)(12) + Wang–Isola 的 $\mathcal L_{\text{align}}(f;2)=\mathbb E\|f(x)-f(y)\|^2$（成对平方在对比文献里是**有名字的一等对象**）。
**在什么条件下它才是正当的（全部可检查）**：
1. $A_r$ **只由训练集**估出、冻结或 EMA，验证/评估 batch 不改 $A_r$（否则 $r$ 与方向随 batch 漂移，M1 的不可识别性立即生效）；
2. $r\le 11$ 且 $r$ **在看结果前登记**；$n$ 与 $\widehat\Sigma_L^{-1}$ 条件数记录在案（$n\lesssim 512$ 时必须 ridge/稀疏，并声明它改变了被选子空间——M2 的失败模式）；
3. 尺度锚**双向**：$Z_H$ 用 train-only 固定仿射（逐维 z-score，均值方差来自训练集且**不随 batch 更新**）；$Z_L$ 过 LayerNorm 后其 RMS 记入日志。且实现上**禁止** $Z_L\to sZ_L$ 与 $A_r\to A_r/s$ 同时改变（若可，则 A=0，走 F-A）；
4. 目标向量残差（11 维）与标量任务目标不混用；不得把 $\mathcal L^{\text{C1}}$ 写成模型 D 的标量 $D$（见 §4.3）；
5. 报告映射方向（$512\to11$）+ 收缩因子 $\sigma^2/(\sigma^2+\lambda)$（M9）。
**五位**：`P=1 A=1(条件 3) H=可判 B=不涉及 S=0`（残差是多维）→ 路由 11110，主风险仍须按 F-S 逐目标处理。

### C2（主）**对齐对象改为"预测"而非"表征"：低频上下文可实现的盘口条件均值一致性**

$$\ \mathcal L_{\text{align}}^{\text{C2}}=\bigl\|\,m_H(Z_H)-m_L(Z_L)\,\bigr\|^{2},\qquad m_H,m_L\ \text{为各自 head 的仿射输出}\ $$

血统：Hinton KD (1)(2)（蒸馏的是**条件分布**不是表征）、IRM（"a data representation such that the **optimal classifier on top** of that data representation, is the same for all environments"）、CDAN/MDD（只对齐特征边缘分布不足）。
**正当条件**：
1. 两个 head **都是仿射且可比**（同一目标或同一充分统计量），否则 $\|m_H-m_L\|^2$ 不是"信息一致"而是"两个单位不同的量之差"——必须先做 H 位（线性探针 vs 部署头风险差 $\le\epsilon_H$）；
2. 明确 $m_H$ 是**教师**（训练时可得、部署时未必）还是**双部署**（决定 B 位）；
3. 该项**不测表征对齐**，因此不能用它证明"低频与高频在同一空间"；它能证明的是"低频支路足以复现高频支路的**预测**"——正是项目真正关心的量。
**五位**：`P=可判(成对平方，但对象是预测) A=可判(头的仿射系数即锚) H=1 B=取决于部署 S=1(若目标标量)`。**这是唯一能把"私有成分是否必须对齐"变成可测问题的候选**（C-CM-004 §5 的 ❌ 条目之一）。

### C3（主，**降级为诊断**）正则化 CCA / SVCCA 典型相关（含 null 校准）

**正当条件**：只当它被登记为**监控量而非损失项**时使用。必须同时报告 (i) 样本典型相关 $\{\hat\rho_i\}$、(ii) 同维度**打乱配对**的 null 分布（Bykhovskaya–Gorin / Wachter 表明非打乱也会非零）、(iii) $n$ 与 $512$ 的比。缺 (ii) 时 $\hat\rho>0$ 不构成任何证据（Lopez-Paz："the finite-sample version ... is constant and equal to "1" for continuous random variables"）。
**五位**：`P=0`（强制）→ 走 F-P，与 $D$ 的单调结论不得互借。

### C4（消融）**InfoNCE / NT-Xent 跨源对比（$Z_L\leftrightarrow Z_H$ 双向，温度扫描）**
用途：检验"**成对**约束是否真的重要"——对比损失去掉配对后（只对齐 $\tau$-softmax 检索）性能是否不变。必登记 $\tau$ 与 batch size，并做 $\tau\in\{1/10,1\}$ 两档（Liang：gap 距离随 $\tau$ 单调变化）。
**五位**：`P=0 A=0(球面化消灭 Var) H/B 不涉及 S=不涉及` → 纯消融。

### C5（消融）**MMD / 核均值边缘分布对齐（含 mMD 特例 = 均值之差平方）**
用途：把 C-CM-004 §1 T5（"边缘分布不决定配对结构"）做成**可跑**的反例基线；同时给"$D$ 下降是否只因为分布靠拢"提供一个明确的对照。注意线性核 mMD 退化为 $\|\mu_L-\mu_H\|^2$，与 C1 的残差不是一回事（后者是逐样本配对）。
**五位**：`P=0 A=0`。

> **未列为候选而明确排除的**：kernel CCA（M3，$\kappa$ 决定一切且 $k\ge n$ 即失效）；RKD/SP 关系型（M6，构造性尺度不变 → A=0）；DTW（M10-5，非度量 + 允许时点重对齐 = 前视风险）；任何 MI 估计器作为目标（M8，$O(\ln N)$ 天花板）。

---

## 3. 对齐对象问题（representation vs prediction）的文献结论

**结论：文献明确讨论过，且方向一致——"对齐表征"与"对齐预测/条件分布"是两个不同的对象；前者的可识别性更弱，且其弱可识别性不损害预测性能。** 逐条：

1. **[一手] 高斯下 CCA 的不可识别性与预测性能解耦。** Podosinnikova–Bach–Lacoste-Julien, arXiv:1602.09013：
   > "Gaussian CCA is only identifiable up to multiplication by any invertible matrix. **Although this unidentifiability does not affect the predictive performance of the model**, it does affect the factor loading matrices and hence the interpretability of the latent factors."
   → 项目含义：这正是 $\delta=0$ 与 $\delta>0$ 之争的文献表述——"表征空间的对齐自由度"与"预测性能"是**可分离的**；把对齐项当作"必须消灭的偏差"缺依据。
2. **[一手] 相似性指标若对可逆线性变换不变，则在维数 > 样本数时测不到有意义的内容。** Kornblith et al., arXiv:1905.00414 摘要（§M1 引用）。项目 512 维 vs 微调样本量 → 用任何不变型指标（CCA/Procrustes/CKA）作**验收**都必须先确认 $n>p$，否则应改用"探针性能差"作验收（=H 位）。
3. **[一手] IRM 直接否定"对齐表征分布"这一对象。** Arjovsky et al., arXiv:1907.02893：
   > "we could adopt a domain adaptation strategy, and estimate a data representation $\Phi(X_1,X_2)$ that follows the same distribution for all environments. This would fail to find the true invariance in Example 1... **This illustrates why techniques matching feature distributions sometimes attempt to enforce the wrong type of invariance**..."
   > "our goal is to learn correlations invariant across training environments. For prediction problems, this means **finding a data representation such that the optimal classifier ... on top of that data representation, is the same for all environments**."
   → 项目含义：把 $Z_H,Z_L$ 的分布靠拢，属于文中点名"会强制错误不变性"的一类；**若要对齐的是"最优头一致"**，才是被该文认为正确的对象。项目 $\delta>0$ 若采用 C2 形式即落在 IRM 一侧。
4. **[一手] 只对齐特征边缘分布对多峰不足，需要 (feature, prediction) 的联合对齐。** Long et al., CDAN, arXiv:1705.10667：
   > "when the feature distribution is multimodal, which is a real scenario due to the nature of multi-class classification, **adapting only the feature representation may be challenging**"
   > "this risk **cannot be tackled by aligning distributions of features and classes via separate domain discriminators**, since the multimodal structures can only be captured sufficiently by the **cross-covariance dependency between the features and classes**"
   > "Superior than concatenation, the multilinear map $\mathbf{x}\otimes\mathbf{y}$ can fully capture the multimodal structures behind complex data distributions."
   同族理论界：Zhang et al., arXiv:1904.05801 的 MDD (13) 把差异度定义在**判别函数**上而非特征分布上。
   → 项目含义：盘口特征明显多峰（竞价/连续/涨跌停/事件），"只对齐特征"的失效条件在此完全成立。
5. **[一手] 蒸馏一族把对象明确放在条件分布。** Hinton et al., arXiv:1503.02531：
   > (1) `$q_{i}=\frac{exp(z_{i}/T)}{\sum_{j}exp(z_{j}/T)}$` ; (2) `$\frac{\partial C}{\partial z_{i}}=\frac{1}{T}\left(q_{i}-p_{i}\right)$`
   > "The relative probabilities of incorrect answers tell us a lot about how the cumbersome model tends to generalize."
6. **[一手-子代理] 对随机表征，比较对象应是"整条条件分布"而非"平均响应"。** Duong et al., *Representational dissimilarity metric spaces for stochastic neural networks*, ICLR 2023, arXiv:2211.11665：
   > "**Existing methods compare deterministic responses ... or averaged responses ... However, these measures of deterministic representational similarity ignore the scale and geometric structure of noise**, both of which play important roles..."
   → 项目含义：$Z_H$（11 维统计量）带显著观测噪声（模型的 $\nu$）；只比较均值/点估计会丢掉 $\nu$ 的信息——这与 C-CM-004 §7 的"$\mathrm{Var}(Z_i)=1+\nu$ 必须固定"是同一件事的两个面。
7. **反向证据（说明"对齐表征"不总是白做工）**：Zimmermann et al., arXiv:2102.08850：InfoNCE 最优解 $f=\mathbf A g^{-1}$（up to 正交），即表征几何确实携带生成因子的逆——**但其前提是"观测由某潜变量经光滑 $g$ 生成"**，$Z_H$ 是人工统计量，前提不成立；该文自身亦承认 "On real data, it is unlikely that the assumed model distribution $q_h$ can exactly match the ground-truth conditional."
8. **检索缺口（如实报告）**：提示中暗示的"对齐表征但预测头各用各的"的**显式**讨论，本轮**未找到逐字命中**的单一文献——找到的是三条各自覆盖一部分的证据（IRM 的"最优头一致"、CDAN/MDD 的"特征边缘对齐不足"、PCC 类的"表征几何 vs 探针性能"）。文献里被点名却**未能核实**的两个候选（Dreesen et al. 的 Predictability Comparability Criterion；Kluger 组的"conditional-distribution similarity"）列 §5。**因此本项目的 $\delta=0$/$\delta>0$ 问题在文献中不是已解决问题，而是有明确方向性证据的开放接口**——这条判断本身可作为对外表述。

---

## 4. 与模型 D 的兼容性（高斯双源闭式下哪个候选仍有解析结构）

模型 D 的可迁移对象（C-CM-004 §3、DS-CM-001 §0）：$D=2(\theta+\nu)$，$u^2=\frac{(\sqrt{1-\theta}+\kappa\sqrt\theta)^2}{1+2\kappa^2}$，$R_H=1-\frac{u^2}{1+\nu}$，$R=1-\frac{2u^2}{2+\nu-\theta}$，$\Delta I=\tfrac12\ln\frac{R_H}{R}$。前提 `G`（线性高斯、独立噪声、$\nu>0$ 固定、目标方差归一化）未被确认，以下只在"**若 G 成立**"下讨论。

### 4.1 **兼容：C1（线性映射成对平方）**
取 $X=Z_L\in\mathbb R^{512}$、$Y=Z_H\in\mathbb R^{11}$、联合高斯。$\mathcal L^{\text{C1}}$ 的最小化对 $A$ 是**纯二次**：
$$A^\star=\Sigma_{L}^{-1}\Sigma_{LH},\qquad \min_A \mathbb E\|Z_H-Z_LA\|^2=\operatorname{tr}\Sigma_H-\operatorname{tr}\!\bigl(\Sigma_{HL}\Sigma_L^{-1}\Sigma_{LH}\bigr)$$
即 Donnat–Tuzhilina 式 (12) 的总体版本（逐字见 §M2）。**解析结构完全保留**：秩 $r$ 约束下由 $\Sigma_L^{1/2}A^\star\Sigma_H^{-1/2}$ 的奇异值给出 $\rho_i$，残差 $\sum_j(\sigma_{H,j}^2-\text{解释项})$。
**但必须写清三件事**：
1. **$A\neq I$ ⇒ 项目 $D$ 不等于模型 D 的 $D$。** 模型 D 的 $D=2(\theta+\nu)$ 是**同一坐标、同尺度**下的 $L^2$ 距离；带 $A_r$ 之后它是"$Z_H$ 中不可被 $\sigma(Z_L)$ 线性解释的方差"，量纲/单位随 $A_r$ 改变。DS-CM-001 §2 第 3 步要求"固定倍数的配对平方项"——$A_r$ 不是常数倍，**因此严格说 P 位应在"$A_r$ 冻结后视 $Z_LA_r$ 为低频侧表示"的意义下判 1，并在证据栏写明"$Z_L$ 已被 $A_r$ 预处理"**。这是一个诚实的限定，不是通过。
2. **$r\le 11$，$q=11\le p=512$ 正是 M2 的适用域**——本项目的维度不对称**有利于**该候选的一致性定理成立（其卖点即"one of the datasets is high-dimensional while the other remains low-dimensional"，见 §M1/§M2 引文）。这是本轮最强的一条"文献与项目形状吻合"的证据。
3. 目标为**向量残差**，不是标量 → **S=0**，走 F-S：不得把 $\sum_{j=1}^{11}$ 的对角和称为模型 D 的标量 $D$。要落到 D 路由，需另加"各向同性 + 按维平均"的**预登记**约定。

### 4.2 **部分兼容：C2（预测层对齐）**
标量目标下 $\mathcal L^{\text{C2}}=(m_H-m_L)^2$ 是**真正的成对平方**且是标量（S=1）。在模型 D 内 $m_H,m_L$ 即 Bayes 仿射头，其差的平方期望可由 $\Sigma$ 直接闭式给出（因头是线性、高斯）。**但它测的是"两路预测的一致"，不是模型 D 的 $D=\mathbb E\|Z_H-Z_L\|^2$** —— 二者在 D 中是不同的量，不可混记。它对应的可解析对象其实是 $R_H$ 与 $R$ 的关系（嵌套风险），而 C-CM-004 §7 的"部署时两路都用"正是决定用哪一个的位。
→ 若采用 C2，**DS-CM-001 的 `D_hat` 监控量要重新定义**（现在的 `D_hat` 定义是"配对平方差"），否则会静默地把预测一致度当表示距离读。

### 4.3 **不兼容（保留为诊断/消融）**：C3（CCA）、C4（InfoNCE）、C5（MMD）、M3（KCCA）、M6（RKD）
- CCA/RKD/MMD 的"下降"在高斯双源下**没有** $\theta$ 的单调映射；MMD 更与配对结构无关（§M7）。
- InfoNCE：其值到 MI 的换算被 $\mathrm{O}(\ln N)$ 界与指数方差双重否证（§M8-1/2），因此"$\Delta I$ 用 InfoNCE 估"不成立；**$\Delta I$ 只能用 $R_H/R$ 闭式**（这恰是项目已有物，见 C-CM-004 §1.5）。
- M11（PCME 型 $\sigma$ 头）不产生 $D$ 的解析式，但**提供 $\nu$ 的经验实现物**，是检验 `G` 中"$\nu$ 固定"的前提能否被审计的最短路径。
- **C-T9-002 的迁移检查**：其定理 2/3 的坍塌结论针对"到固定先验的边缘 KL / 条件 KL 平均"（分支 A/B）。本表 **C1–C5 全部属于分支 C（跨源一致性）**，故 C-T9-002 §8 的 ❌ 条目全部生效：**不得**用 A/B 的阈值 $\sigma=\tau$ 论证本表候选的行为。唯一可迁移的是其方法论要求：先固定尺度（→ §2 C1 条件 3）。

---

## 5. 未能核实的点（逐条，未核不引）

| # | 未核实项 | 已做到哪一步 | 影响 |
|---|---|---|---|
| U1 | 高斯下 $I=\sum_i-\tfrac12\ln(1-\rho_i^2)$（典型相关↔互信息）的**逐字出处** | 在已 fetch 的 5 篇 CCA 文献中未命中该式 | §4.3 引用 CCA↔$\Delta I$ 时**只可写"项目自有 G2 闭式"**，不得写"经典结果见 X" |
| U2 | Donnat–Tuzhilina 稀疏惩罚的**具体估计量与速率条件**（§M2 只取 Lemma1/Theorem2 与摘要） | 未取该节正文 | C1 条件 2 里"用稀疏而非 naive ridge"目前是方向性建议，不是被核实的技术配方 |
| U3 | KCCA 在 $\kappa\to0$ 速率下的渐近一致性定理 | 未取得；只取到"必须正则 / 会过拟合 / $k\ge n$ 出现伪完全相关"三条否定式 | 对 KCCA 的负面结论**不依赖** U3，可安全使用 |
| U4 | "小 batch 跨源对比产生 spurious/shortcut 对齐"的 2023–2025 **专门分析文献** | 只核到 Liang 2022 的 repulsive structure + 后处理改 gap + Wang–Liu 的 uniformity-tolerance；未找到以"跨源小 batch 假负样本"为主题的论文 | §2 C4 的"高频相邻时点负样本高度自相关"是**本文件的推断**，必须标 [项目推论] 而非 [文献] |
| U5 | Tung & Hung, *Similarity-Preserving KD* (arXiv:1907.09682) 的式子 | **ID/作者/日期 [一手] 核对**（`1907.09682v2 | 2019-07-23 | Frederick Tung`），正文公式未 fetch | 该条只作为"关系型对齐已发表"的旁证，不引其形式 |
| U6 | MMD 的特征核条件与 $\mathrm{MMD}=0\iff p=q$ 的逐字定理 | 只取到 eq (1)(2)(3) | §M7 未写该保证 |
| U7 | **MIDAS / U-MIDAS** 原文（混合频率回归的经典表述） | arXiv 检索只命中同族其它论文；经典文（非 arXiv）未取 | §M10-4 关于 MIDAS 的定性判断标 [二手]，写作前须补原文 |
| U8 | Dreesen et al. 的 **Predictability Comparability Criterion**；Kluger 组 **conditional-distribution similarity** | 子代理在 arXiv/ICLR2022 全表/TMLR 全表/Crossref/OpenAlex/OpenReview 均未命中 → **UNVERIFIED，疑为凭记忆构造** | 已从 §3 剔除其引文地位，§3-8 改为"未找到单一显式文献"的如实表述 |
| U9 | Zimmermann 组 **What Does Contrastive Visual Representation Learning Learn? (ICLR 2022)** | 多源检索未命中该标题；命中的是 arXiv:2105.05837 *When Does Contrastive Visual Representation Learning Work?*（**仅标题核对，未读正文**）与 arXiv:2102.08850（已读） | §3-7 只引 2102.08850 |
| U10 | Alam–Fukumizu–Wang (1705.04194) 与 Lopez-Paz (1304.7717) 的**全文核对由子代理完成** | 本文件作者未亲自复核该两页正文（DOI/journal-ref 由子代理 Crossref 核对） | 两处引文标 [一手-子代理]；正式对外引用前须本人复核 ar5iv 页 |
| U11 | FIPP / Global Anchor / PCME / Dinu / Adversarial-Hubness / entropic-DTW 同上（[一手-子代理]） | 同上 | 同上 |
| U12 | "把时序表征对齐"方向**未检索到任何**已发表的"低频 hidden state ↔ 高频盘口统计量"成对平方对齐损失 | 已做多组检索（cross-frequency / mixed-frequency / hierarchical / multiscale + attention / 金融 q-fin），命中的 M10 三篇均无对齐损失 | 支持"候选空间是空白"的主张；**注意这是否定性检索结论，需登记为"检索范围内未见"而非"不存在"** |
| U13 | 模型 D 的既有工具 O / G1 / G2、Guo–Shamai–Verdú 2005 的 I-MMSE、$B=A+I$ 恒等式的**文献出处** | 本轮**未做**（不在 B 的范围） | C-CM-004 §4-3、C-T9-002 §9-2 的缺口仍未关闭，须并入 A/C 组任务 |

---

## 6. 交给 C-CM-004 §7 的直接答复（本文件的净产出）

| C-CM-004 §7 的条件 | 本文件结论 |
|---|---|
| $D$ 必须是成对平方（非对比/MMD） | **可实现**：C1（成对平方 + 冻结线性映射，血统 = Donnat–Tuzhilina (11) 与 Wang–Isola $\mathcal L_{\text{align}}(\cdot;2)$）；C4/C5 明确不满足 |
| $\mathrm{Var}(Z_i)=1+\nu$ 固定 | **可实现但需人工约束**：train-only 逐维仿射 + LayerNorm + 记录 RMS + 禁止同步缩放；文献侧支持 = C-T9-002 §10.6 与 PCME 的 $\mathcal N(0,I)$ 正则 |
| 预测头 = Bayes 最优仿射 | C1 的 $A_r$ 即仿射；但 S 位（11 维向量残差 vs 标量）不通过 → 需预登记"按维平均 + 各向同性"约定，或改用 C2 |
| 部署两路都用 | 与本文件无关（属 B 位的部署重放）；**注意 $A_r$ 在推理期必须可得且冻结**，否则推理用的对齐表示与训练时不是同一对象 |
| 目标一维标量 | 若坚持 C1，$S=0$ → 路由 11110；若要 $S=1$，**只有 C2（预测层）能满足**，代价是放弃"$D$ = 表征距离"的解读 |

**一句话裁定**：**C1 是唯一同时满足 $P=1$ 与"在高斯双源下仍有解析闭式"的已发表候选**（其一致性正定理恰好适用于"$512$ 高维 ↔ $11$ 低维"这一形状，见 §M2 Theorem 2 与其摘要句）；**C2 是唯一能让 $S=1$ 且与"$\delta=0$ 是否已足够"直接对话的候选**；两者不是竞争，是**不同对象的两种 $L_{\text{align}}$**，应按 DS-CM-001 各登记一次、由 `U`（风险差区间）取舍，而不是由理论偏好取舍。
