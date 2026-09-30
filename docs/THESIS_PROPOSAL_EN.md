# Thesis Proposal (Bachelor's Thesis)
## Thesis Title in Czech:
Systém pro monitorování a analýzu dopravy pomocí počítačového vidění

## Thesis Title in English:
System for Traffic Monitoring and Analysis using Computer Vision

### Annotation / Abstract
Traffic data collection, such as traffic density, vehicle types, or pedestrian and cyclist movement, is crucial for planning and optimizing transport infrastructure. Traditional methods, such as manual counting, are time-consuming and prone to errors. A possible solution is the use of an automated system that can analyze video signals from a traffic location in real time, detect and classify various road users (cars, pedestrians, cyclists), and collect data about them.

The aim of the thesis is to design, implement, and test a prototype of a system for the automatic counting and analysis of vehicle and person passages in a defined location. The system will be built on the Raspberry Pi platform with an AI module and will be capable of real-time image processing, i.e., analyzing video signals from a traffic location, detecting and classifying objects (vehicles, pedestrians, cyclists), collecting data about them, and visualizing it in a clear application.

Specific objectives:

* overview of methods for real-time object detection, tracking, and classification (e.g., YOLO, SSD, DeepSORT),
* analysis of available solutions for traffic monitoring,
* design of the system architecture including a camera module, processing unit, and software application,
* data collection and preparation using existing public datasets (e.g., COCO, BDD100K) or creating a custom small dataset for training or fine-tuning the model,
* integration, optimization, and deployment of the model,
* development of software with the following functionality:
    * real-time analysis of the camera video signal,
    * detection of objects passing through a defined line or area,
    * saving data (object type, time, direction) to a database or file,
    * data visualization in the form of graphs and statistics (e.g., in a simple web interface),
* testing and evaluation in a real environment, assessment of detection and counting accuracy compared to manual observation.

The output of the thesis will be a functional device prototype and a software application for traffic monitoring. The output will also include documentation describing the design, implementation, and evaluation of the system's accuracy.

Outline:

Theoretical Part
1. computer vision methods for object detection and tracking
2. overview of systems for traffic data analysis and processing
3. AI on embedded systems (Edge AI)
4. testing methodology and comparison with reference data

Practical Part
1. overall solution architecture
2. selection of hardware for video signal processing
3. design of software components (detection module, database, visualization interface)
4. environment and data preparation
5. configuration and deployment of the detection model
6. development of the application for video processing and data collection
7. creation of the visualization interface
8. definition of a benchmark task, analysis of system accuracy and performance
9. presentation and interpretation of results


### References:

1. LI, En, Liekang ZENG, Zhi ZHOU and Xu CHEN. Edge AI: On-Demand Accelerating Deep Neural Network Inference via Edge Computing. IEEE Transactions on Wireless Communications [online]. 2020, 19(1), pp. 447-457 [cited 2026-02-14]. Available from: doi:10.1109/TWC.2019.2946140
2. LIN, Tsung-Yi, Michael MAIRE, Serge BELONGIE, James HAYS, Pietro PERONA, Deva RAMANAN, Piotr DOLLÁR and C. Lawrence ZITNICK. Microsoft COCO: Common Objects in Context. Lecture Notes in Computer Science [online]. Springer, 2014, 740-755 [cited 2026-04-15]. ISBN 9783319106014. ISSN 0302-9743. Available from: doi:10.1007/978-3-319-10602-1_48
3. REDMON, Joseph, Santosh DIVVALA, Ross GIRSHICK and Ali FARHADI. You Only Look Once: Unified, Real-Time Object Detection. 2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR) [online]. IEEE, 2016, 779-788 [cited 2026-02-13]. Available from: doi:10.1109/cvpr.2016.91
4. WOJKE, Nicolai, Alex BEWLEY and Dietrich PAULUS. Simple online and realtime tracking with a deep association metric. 2017 IEEE International Conference on Image Processing (ICIP) [online]. IEEE, 2017, 2017, 3645-3649 [cited 2026-02-13]. Available from: doi:10.1109/icip.2017.8296962
5. ZHOU, Wei, Li YANG, Lei ZHAO, Runyu ZHANG, Yifan CUI, Hongpu HUANG, Kun QIE and Chen WANG. Vision Technologies with Applications in Traffic Surveillance Systems: A Holistic Survey. ACM Computing Surveys [online]. Association for Computing Machinery (ACM), 2025, 2025-9-9, 58(3), 1-47 [cited 2026-02-13]. ISSN 0360-0300. Available from: doi:10.1145/3760525
6. WEN, Longyin, Dawei DU, Zhaowei CAI, et al. UA-DETRAC: A new benchmark and protocol for multi-object detection and tracking. Computer Vision and Image Understanding [online]. Elsevier BV, 2020, 193, 102907 [cited 2026-04-15]. ISSN 1077-3142. Available from: doi:10.1016/j.cviu.2020.102907