# Viva Questions and Answers (55)

Figures quoted below come from this project's trained model (SVM: accuracy 92.5 %, precision 91.1 %, recall 94.8 %,
F1 92.9 %, ROC-AUC 0.982; energy saving 28.6 % in simulation). If you retrain with other settings, quote your own numbers
from `reports/metrics.json` and `reports/energy_summary.json`.

---
## A. Project overview

**1. What is your project about?**
It predicts whether a crop needs irrigation from temperature, humidity, soil moisture, rainfall and crop type using an SVM, then calculates pump status, water volume and electricity used and saved compared with a fixed timer.

**2. What problem does it solve?**
Timer-based irrigation wastes water and pump electricity on days when the soil is already wet, and under-waters on hot, dry days. Our system switches the pump on only when needed.

**3. What is "electrical optimisation" in your project?**
Using the pump's power rating and flow rate to convert the required water into run-time and kWh, and comparing it with a conventional 2-hour daily timer (3.0 kWh). The difference is the saving.

**4. Who are the users?**
Farmers or farm managers who enter field readings in a web page; in future an ESP32/Raspberry Pi could call the same API automatically.

**5. Which tools and libraries did you use?**
Python, Pandas, NumPy, Scikit-learn, Matplotlib, Joblib, Flask, HTML/CSS/Bootstrap 5.

**6. What is the architecture of the system?**
Sensors → cleaning/scaling → SVM classifier → electrical optimisation module → Flask web server → browser (and optionally a pump relay).

**7. Is the system connected to real hardware?**
No. It is a software prototype; the pump is a numerical model. Relay and sensor integration is listed as future scope.

## B. Dataset and preprocessing

**8. Which dataset did you use?**
A synthetic dataset of 5,000 days that we generated (`src/generate_dataset.py`), because no open dataset had exactly these columns.

**9. Why synthetic? Is that acceptable?**
It is acceptable for demonstrating a methodology if stated clearly. We state that accuracy reflects how well the model learns our generating rules and is not field accuracy. Replacing the CSV with real data and re-running training is all that is needed.

**10. How was the label (Irrigation Needed) created?**
From a water-stress score: crop moisture threshold minus soil moisture, plus non-linear heat, humidity-temperature and saturating-rain terms, plus Gaussian noise. Score > 0 means irrigation needed.

**11. Why did you add noise?**
To imitate sensor errors and day-to-day variation; without noise the problem would be trivially separable and results unrealistic.

**12. What attributes does the dataset have?**
temperature (°C), humidity (%), soil_moisture (%), rainfall (mm), crop_type (5 crops), irrigation_needed (0/1).

**13. What data-cleaning steps did you perform?**
Removed duplicates, converted columns to numeric, turned impossible readings into missing values, filled missing values with the crop-wise median, and dropped rows with missing label/crop.

**14. Why median and not mean for missing values?**
The median is not distorted by outliers such as sensor spikes.

**15. How many rows were missing/duplicated?**
50 duplicates removed and 435 missing/invalid sensor values filled; 5,000 clean rows remained.

**16. What is feature scaling and why do you need it?**
Rescaling each feature to mean 0 and standard deviation 1 (`StandardScaler`). SVMs use distances, so a feature with a large range (rainfall 0–300) would dominate one with a small range.

**17. How did you encode the crop type?**
One-hot encoding: one 0/1 column per crop, so the model does not assume an order between crops.

**18. What is data leakage and how did you avoid it?**
Using information from the test set during training. We placed scaling and encoding inside a scikit-learn `Pipeline`, so the scaler learns mean/std from training data only.

**19. Is the dataset balanced?**
Yes: about 48 % "No" and 52 % "Yes", so accuracy is a meaningful metric.

**20. What did EDA tell you?**
Soil moisture has the strongest relation to the label (correlation about −0.65); temperature increases the need; rain decreases it; the decision boundary in soil-moisture/temperature space is curved.

## C. Support Vector Machine

**21. What is an SVM?**
A supervised classifier that finds the separating boundary (hyperplane) with the maximum margin between classes.

**22. What are support vectors?**
The training points that lie on or inside the margin; they alone define the boundary.

**23. What is the margin and why maximise it?**
The distance between the boundary and the nearest points of each class (2/‖w‖). A larger margin usually generalises better to unseen data.

**24. What is a soft margin and what does C do?**
Soft margin allows some misclassified points. C is the penalty for errors: large C → fewer training errors, narrow margin, risk of over-fitting; small C → wider margin, more tolerance.

**25. What is the kernel trick?**
Computing inner products in a higher-dimensional space through a kernel function without explicitly transforming the data, so a linear separator there becomes a non-linear boundary in the original space.

**26. Which kernel did you use and why?**
RBF, K = exp(−γ‖x−x′‖²), because the heat/humidity/rain effects are non-linear and RBF needs no manual feature engineering.

**27. What does gamma do?**
It sets the reach of one training point. High gamma → very local, wiggly boundary (over-fit); low gamma → smooth boundary.

**28. Which C and gamma did you select and how?**
C = 50, gamma = 0.02, chosen by 5-fold cross-validated grid search scored on F1, using only training data.

**29. Can an SVM give probabilities?**
Not natively. scikit-learn applies Platt scaling (`probability=True`), fitting a sigmoid to the decision scores. We show it as "confidence".

**30. Why is the SVM sensitive to scaling but a decision tree is not?**
SVM depends on distances/dot products; a tree uses one-feature threshold splits that are unaffected by monotonic scaling.

**31. What are the disadvantages of SVM?**
Training is slow on very large datasets (roughly quadratic), needs scaling and hyper-parameter tuning, and is less interpretable than a tree or logistic regression.

**32. Why did you choose SVM over a neural network?**
For about 5,000 samples and 5 features an SVM is simpler, trains quickly, needs less tuning data and is easier to explain; a neural network offers no clear benefit here.

## D. Model comparison and metrics

**33. Which models did you compare?**
SVM, Decision Tree, Random Forest and Logistic Regression, all with the same pipeline, grid search and test set.

**34. Which performed best?**
SVM had the highest F1 (92.9 %), recall (94.8 %) and ROC-AUC (0.982). Logistic Regression was very close (F1 92.5 %).

**35. Is the SVM really better than Logistic Regression?**
Only slightly: the difference (0.4 points) is smaller than the cross-validation standard deviation, so we say they are comparable with a slight edge to SVM. We chose SVM also because it handles non-linearity and gives a compact model.

**36. Why is the decision tree the weakest?**
A single tree approximates a curved boundary with axis-parallel steps and is prone to over-fitting.

**37. Define accuracy, precision, recall and F1.**
Accuracy = (TP+TN)/all; Precision = TP/(TP+FP); Recall = TP/(TP+FN); F1 = harmonic mean of precision and recall.

**38. What is a confusion matrix? What are yours for the SVM?**
A table of actual vs predicted classes. SVM test set: TN 436, FP 48, FN 27, TP 489.

**39. Which is worse here, a false positive or a false negative?**
A false negative (thirsty crop not watered) risks yield; a false positive wastes water and energy. Hence recall matters, and the SVM has the highest recall.

**40. What is ROC-AUC?**
The area under the true-positive-rate vs false-positive-rate curve across all thresholds; 1.0 is perfect and 0.5 is random.

**41. What is cross-validation and why use it?**
Splitting the training data into k folds, training on k−1 and validating on one, rotating. It gives a more reliable estimate and is used to choose hyper-parameters without touching the test set.

**42. What is over-fitting and how did you control it?**
Memorising training data and failing on new data. Controls: soft margin C, small gamma, cross-validated tuning, a held-out test set, tree depth limits.

**43. Why stratified split?**
It keeps the class proportions the same in train and test sets.

**44. Why is `random_state = 42` used?**
To make results reproducible; the same seed gives the same split and model.

## E. Electrical optimisation

**45. How do you calculate water required?**
V = (target moisture − soil moisture) × 300 L/% × crop factor × heat factor − 100 L/mm × rainfall, bounded between 500 L and 1.5 × the timer volume.

**46. How do you calculate electricity consumption?**
Run-time = V / pump flow (3000 L/h); energy = pump power (1.5 kW) × run-time.

**47. What is the baseline?**
A timer system running the pump 2 h/day: 2 × 1.5 = 3.0 kWh/day (6000 L).

**48. What saving did you get?**
About 28.6 % average pump energy saving over 1,000 simulated test days, under these assumptions.

**49. The smart system used more energy than the timer on many days. Why?**
On very hot/dry days the crop needs more than the timer's 2 h. The system moves energy from days it is unnecessary to days it is needed; it is not meant to be cheaper on every day.

**50. Are the pump numbers real?**
They are assumptions (1.5 kW, 3000 L/h, 100 m² plot) stored in `config.py`; replace them with your pump's data sheet and measured values.

## F. Web application and code

**51. What does Flask do in your project?**
It is the web server: it renders the pages, validates the form, calls the saved model and returns the prediction (HTML and a JSON API).

**52. What is Joblib and why save the whole pipeline?**
Joblib serialises Python objects efficiently. Saving the whole pipeline keeps the scaler and encoder together with the SVM so new inputs are transformed exactly as in training.

**53. How is input validated?**
HTML5 min/max in the browser, and again in Python (`validate()`) because browser checks can be bypassed; invalid input returns an error message instead of a prediction.

**54. What is the JSON API?**
`POST /api/predict` with temperature, humidity, soil_moisture, rainfall and crop; it returns the prediction, pump status, litres, kWh used and saved. A microcontroller could call it.

**55. What are the limitations and future scope?**
Limitations: synthetic data, assumed pump/timer values, single-day decision, no hardware. Future: real sensor data, ESP32 + relay + power meter, weather forecasts, regression for water volume, solar/tariff-aware scheduling.

## Bonus questions
**56. How would you adapt the project to a new crop?** Add it to `CROPS` in `config.py` with a threshold and water factor, regenerate/collect data and retrain.
**57. How would you reduce false negatives further?** Lower the decision threshold on the probability (e.g. irrigate when P ≥ 0.4), or use class weights.
**58. Why is your project original?** The data, code, electrical model, comparison and documentation were written for this project; algorithms and libraries are standard and cited in the references.
