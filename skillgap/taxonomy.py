"""Skill taxonomy for data science, software, and robotics roles.

Built from the Nov 13 2026 snapshot: candidate terms were measured against 2,737 cleaned
postings and kept when they appear in roughly 1% or more of any role family, plus a few
low-frequency skills the curricula teach (so coverage can be scored both ways).

Alias syntax
  "spark streaming"   case-insensitive phrase; spaces, hyphens and slashes are interchangeable
  "=Excel"            case-sensitive phrase (for words that are also ordinary English)
  "re:..."            case-insensitive regular expression
  "re=..."            case-sensitive regular expression
The canonical skill name itself is NOT matched automatically: list every surface form.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LANGS = r"(?:Python|Java|C\+\+|C#|Rust|Scala|Kotlin|TypeScript|JavaScript|Ruby|Swift|SQL|MATLAB|Julia|Go)"


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


_RAW: dict[str, dict[str, list[str]]] = {
    "Programming languages": {
        "Python": ["python"],
        "SQL": ["=SQL", "t-sql", "pl/sql", "sql queries"],
        "Java": ["re=\\bJava\\b(?!\\s*Script)"],
        "C++": ["c++", "cpp", "modern c++"],
        "C": ["re=\\bC(?=\\s*/\\s*C\\+\\+)", "re=\\bC(?=,\\s*C\\+\\+)", "re=\\bC(?= and C\\+\\+)", "=embedded C",
              "=ANSI C", "=C programming", "re=\\bC(?=,\\s*" + LANGS + ")", "re=(?<=, )C(?=,| and| or)"],
        "Go": ["golang", "re=\\bGo(?=\\s*(?:,|/|\\bor\\b|\\band\\b)\\s*" + LANGS + ")",
               "re=(?<=, )Go\\b(?=,| and| or|\\))", "re=(?<=or )Go\\b(?=[,.)]|$)"],
        "Rust": ["=Rust"],
        "Scala": ["=Scala"],
        "Kotlin": ["kotlin"],
        "TypeScript": ["typescript"],
        "JavaScript": ["javascript", "=JS", "ecmascript"],
        "C#": ["c#", ".net", "dotnet"],
        "R": ["re=\\bR(?=\\s*(?:,|/|\\bor\\b|\\band\\b)\\s*(?:Python|SQL|Julia|SAS|MATLAB))",
              "re=(?<=Python, )R\\b", "re=(?<=Python or )R\\b", "re=(?<=Python and )R\\b",
              "=R programming", "=RStudio", "tidyverse"],
        "MATLAB": ["matlab", "simulink"],
        "Bash / shell": ["bash", "shell scripting", "shell scripts", "zsh"],
        "Ruby": ["=Ruby", "ruby on rails", "=Rails"],
        "Swift": ["=Swift", "swiftui"],
    },
    "Machine learning and statistics": {
        "Machine learning": ["machine learning", "=ML", "ml models", "ml systems"],
        "Deep learning": ["deep learning", "neural networks", "neural network", "deep neural"],
        "Reinforcement learning": ["reinforcement learning", "=RL", "policy gradient", "ppo"],
        "Statistics": ["statistics", "statistical", "hypothesis testing", "statistical modeling",
                       "statistical inference"],
        "Probability and Bayesian methods": ["probability", "probabilistic", "bayesian",
                                             "stochastic processes", "markov"],
        "Experimentation and A/B testing": ["a/b testing", "a/b tests", "a/b test", "ab testing",
                                            "experimentation", "experiment design", "online experiments"],
        "Causal inference": ["causal inference", "causality", "causal modeling", "uplift modeling"],
        "Time series and forecasting": ["time series", "time-series", "forecasting"],
        "Recommender systems": ["recommender systems", "recommendation systems", "recommender system",
                                "recommendation system", "recommendations engine", "collaborative filtering"],
        "Search and ranking": ["information retrieval", "search ranking", "search relevance", "learning to rank",
                               "ranking models", "ranking systems", "search engine", "search systems"],
        "Anomaly detection": ["anomaly detection", "outlier detection", "fraud detection"],
        "Mathematical optimization": ["convex optimization", "numerical optimization", "linear programming",
                                      "integer programming", "operations research", "optimization algorithms",
                                      "mathematical optimization", "combinatorial optimization"],
        "Linear algebra": ["linear algebra", "matrix factorization", "eigen"],
        "Classical ML methods": ["regression", "classification", "clustering", "supervised learning",
                                 "unsupervised learning", "decision trees",
                                 "random forest", "gradient boosting", "support vector", "svm"],
        "Feature engineering": ["feature engineering", "feature stores", "feature store"],
        "Data mining": ["data mining", "pattern mining", "association rules"],
    },
    "Generative AI and LLMs": {
        "Large language models": ["large language models", "large language model", "=LLM", "=LLMs",
                                  "foundation models", "foundation model", "language models"],
        "Generative AI": ["generative ai", "genai", "gen ai", "generative models"],
        "Fine-tuning and post-training": ["fine-tuning", "fine tuning", "finetuning", "fine-tune", "post-training",
                                          "rlhf", "instruction tuning", "lora", "dpo"],
        "Retrieval-augmented generation": ["retrieval-augmented generation", "retrieval augmented generation",
                                           "=RAG"],
        "Prompt engineering": ["prompt engineering", "prompt design", "prompting"],
        "Embeddings and vector search": ["embeddings", "vector search", "semantic search", "vector database",
                                         "vector databases", "pgvector", "pinecone", "faiss", "milvus", "weaviate"],
        "AI agents": ["ai agents", "llm agents", "agentic", "multi-agent", "agent frameworks", "agent systems",
                      "autonomous agents", "tool use", "tool calling", "langgraph"],
        "LLM frameworks": ["langchain", "llamaindex", "llama index", "dspy"],
        "Model evaluation": ["model evaluation", "evals", "llm evaluation", "evaluation frameworks",
                             "evaluation pipelines", "benchmarking models"],
        "Transformers": ["transformer models", "transformer architectures", "transformer architecture",
                         "transformers", "attention mechanisms"],
        "Diffusion models": ["diffusion models", "diffusion model", "stable diffusion"],
        "Multimodal models": ["multimodal", "multi-modal", "vision-language", "vision language models"],
        "NLP": ["natural language processing", "=NLP", "text classification", "named entity recognition",
                "sentiment analysis"],
        "Inference optimization": ["inference optimization", "model inference", "quantization", "distillation",
                                   "model compression", "pruning", "speculative decoding", "kv cache", "vllm"],
    },
    "ML frameworks and MLOps": {
        "PyTorch": ["pytorch", "torch"],
        "TensorFlow": ["tensorflow", "keras"],
        "JAX": ["=JAX", "flax"],
        "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
        "Hugging Face": ["hugging face", "huggingface"],
        "Gradient boosting libraries": ["xgboost", "lightgbm", "catboost"],
        "GPU programming (CUDA)": ["cuda", "gpu programming", "gpu kernels", "triton kernels", "cudnn"],
        "Model serving": ["model serving", "tensorrt", "onnx", "triton inference", "torchserve", "inference server",
                          "inference serving"],
        "MLOps": ["mlops", "mlflow", "kubeflow", "model deployment", "model monitoring", "ml pipelines",
                  "ml infrastructure", "sagemaker", "vertex ai"],
        "Distributed training": ["distributed training", "data parallel", "model parallel", "fsdp", "deepspeed",
                                 "megatron", "=Ray", "multi-gpu", "multi-node training"],
    },
    "Data engineering": {
        "Spark": ["spark", "pyspark", "spark sql"],
        "Kafka and streaming": ["kafka", "flink", "kinesis", "pub/sub", "stream processing", "streaming data",
                                "event streaming"],
        "Workflow orchestration": ["airflow", "dagster", "prefect", "luigi", "argo workflows"],
        "dbt": ["=dbt"],
        "ETL / data pipelines": ["etl", "elt", "data pipelines", "data pipeline", "data ingestion"],
        "Data warehousing": ["data warehouse", "data warehouses", "data warehousing", "snowflake", "bigquery",
                             "redshift", "synapse"],
        "Databricks and lakehouse": ["databricks", "lakehouse", "delta lake", "iceberg", "apache hudi"],
        "Data modeling": ["data modeling", "data modelling", "dimensional modeling", "schema design", "star schema"],
        "Hadoop ecosystem": ["hadoop", "hive", "hdfs", "mapreduce"],
        "Distributed query engines": ["presto", "trino", "athena", "duckdb"],
        "Big data": ["big data", "large-scale data", "petabyte", "terabytes of data"],
    },
    "Databases": {
        "PostgreSQL": ["postgres", "postgresql"],
        "MySQL": ["mysql", "mariadb"],
        "NoSQL databases": ["nosql", "mongodb", "cassandra", "dynamodb", "couchbase", "scylla", "bigtable"],
        "Redis": ["redis", "memcached"],
        "Elasticsearch": ["elasticsearch", "opensearch", "solr", "lucene"],
        "ClickHouse": ["clickhouse", "druid", "pinot"],
        "Relational databases": ["relational databases", "relational database", "rdbms", "query optimization",
                                 "relational data model", "relational model", "relational algebra", "query evaluation",
                                 "query processing", "indexing and hashing",
                                 "database internals", "transaction processing"],
        "Graph databases": ["graph database", "graph databases", "neo4j"],
    },
    "Cloud and infrastructure": {
        "AWS": ["=AWS", "amazon web services", "ec2", "=S3", "=Lambda"],
        "GCP": ["=GCP", "google cloud", "gke"],
        "Azure": ["=Azure"],
        "Kubernetes": ["kubernetes", "=K8s", "=k8s", "helm"],
        "Docker and containers": ["docker", "containers", "containerization", "containerized"],
        "Infrastructure as code": ["terraform", "pulumi", "cloudformation", "infrastructure as code", "ansible"],
        "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment",
                  "github actions", "jenkins", "buildkite", "gitlab ci"],
        "Linux": ["linux", "unix", "=POSIX"],
        "Observability": ["observability", "prometheus", "grafana", "datadog", "opentelemetry", "monitoring and alerting",
                          "logging and monitoring", "splunk"],
        "Cloud computing": ["cloud computing", "cloud infrastructure", "cloud platforms", "cloud-native",
                            "cloud native", "serverless"],
        "High-performance computing": ["high-performance computing", "high performance computing", "=HPC", "=MPI",
                                       "openmp", "parallel computing", "parallel programming", "simd"],
    },
    "Software engineering": {
        "Distributed systems": ["distributed systems", "distributed system", "distributed computing", "consensus algorithms",
                                "fault tolerance", "fault-tolerant"],
        "System design": ["system design", "systems design", "software architecture", "architecture design",
                          "scalable systems", "large-scale systems"],
        "Microservices": ["microservices", "microservice", "service-oriented"],
        "APIs": ["rest apis", "rest api", "restful", "=REST", "grpc", "graphql", "api design", "apis"],
        "Concurrency": ["concurrency", "concurrent programming", "multithreading", "multi-threaded",
                        "multithreaded", "asynchronous programming", "lock-free"],
        "Software testing": ["unit tests", "unit testing", "integration tests", "integration testing",
                             "test automation", "automated testing", "test-driven", "=TDD", "pytest",
                             "testing frameworks", "end-to-end tests"],
        "Version control (Git)": ["=Git", "=git", "github", "version control", "gitlab"],
        "Code review": ["code review", "code reviews"],
        "Debugging": ["debugging", "debug", "troubleshooting", "root cause analysis"],
        "Performance optimization": ["performance optimization", "performance tuning", "profiling",
                                     "latency optimization", "low-latency", "low latency", "performance engineering"],
        "Frontend development": ["frontend", "front-end", "=React", "react.js", "reactjs", "vue", "angular",
                                 "=HTML", "=CSS", "next.js", "web development"],
        "Backend development": ["backend", "back-end", "server-side", "node.js", "nodejs", "django", "flask",
                                "fastapi", "spring boot"],
        "Mobile development": ["=iOS", "android", "mobile development", "react native", "mobile apps"],
        "Security engineering": ["application security", "cryptography", "cryptographic", "secure coding",
                                 "threat modeling", "vulnerability", "vulnerabilities", "penetration testing",
                                 "=OAuth", "authentication", "encryption", "zero trust"],
        "Networking": ["computer networking", "network protocols", "networking protocols", "=TCP/IP", "=TCP",
                       "=UDP", "=BGP", "=DNS", "network stack", "packet processing"],
        "Compilers and programming languages": ["compilers", "compiler", "=LLVM", "static analysis",
                                                "program analysis", "type systems"],
        "Operating systems": ["operating systems", "kernel", "linux kernel", "device drivers", "virtualization",
                              "hypervisor"],
        "Agile practices": ["agile", "scrum", "kanban"],
        "Site reliability engineering": ["site reliability", "=SRE", "=SREs", "reliability engineering",
                                         "incident response", "incident management", "on-call", "=SLOs", "=SLO"],
    },
    "Data analysis and visualization": {
        "Data visualization": ["data visualization", "visualization", "visualizations", "matplotlib", "plotly",
                               "seaborn", "d3.js"],
        "BI tools": ["tableau", "looker", "power bi", "powerbi", "superset", "mode analytics", "metabase"],
        "Dashboards": ["dashboards", "dashboard"],
        "Excel / spreadsheets": ["=Excel", "spreadsheets", "google sheets"],
        "Pandas / NumPy": ["pandas", "numpy", "scipy", "polars", "dataframes"],
        "Data analysis": ["data analysis", "exploratory data analysis", "=EDA", "data analytics", "analytics"],
        "Data science ethics and privacy": ["responsible ai", "ai ethics", "fairness",
                                            "differential privacy", "algorithmic bias", "bias mitigation"],
    },
    "Robotics and autonomy": {
        "ROS": ["=ROS", "=ROS2", "=ROS 2", "robot operating system"],
        "Robotics simulation": ["simulation", "simulations", "simulator", "gazebo", "isaac sim", "mujoco", "carla",
                                "physics engines", "physics engine"],
        "SLAM and localization": ["=SLAM", "localization and mapping", "visual odometry", "robot localization",
                                  "mapping and localization", "localization algorithms"],
        "State estimation": ["state estimation", "kalman", "extended kalman", "=EKF", "particle filter",
                             "particle filters", "bayesian filtering", "factor graphs"],
        "Sensor fusion": ["sensor fusion", "multi-sensor", "sensor integration"],
        "Perception": ["perception"],
        "Computer vision": ["computer vision", "opencv", "object detection", "image segmentation",
                            "semantic segmentation", "object tracking", "multi-object tracking", "image processing",
                            "visual recognition"],
        "3D vision and point clouds": ["point cloud", "point clouds", "3d reconstruction", "3d vision", "stereo vision",
                                       "camera calibration", "depth estimation", "multi-view geometry", "nerf",
                                       "gaussian splatting"],
        "Motion planning": ["motion planning", "path planning", "trajectory planning", "trajectory optimization",
                            "trajectory generation", "planning algorithms", "behavior planning"],
        "Control systems": ["control systems", "control theory", "feedback control", "controls engineering",
                            "model predictive control", "=MPC", "=PID", "pid control", "pid controller",
                            "nonlinear control", "optimal control", "control loops", "control algorithms"],
        "Kinematics and dynamics": ["kinematics", "inverse kinematics", "rigid body dynamics", "multibody dynamics",
                                    "robot dynamics", "vehicle dynamics", "flight dynamics"],
        "Robotic manipulation": ["robotic manipulation", "grasping", "manipulator", "manipulators",
                                 "dexterous manipulation", "pick and place"],
        "Robot learning": ["robot learning", "imitation learning", "behavior cloning", "sim-to-real", "sim2real",
                           "learning from demonstration", "vision-language-action"],
        "Embedded systems": ["embedded systems", "embedded software", "embedded linux", "firmware",
                             "microcontroller", "microcontrollers", "bare-metal", "bare metal"],
        "Real-time systems": ["real-time systems", "real-time operating system", "=RTOS", "freertos",
                              "real-time embedded", "real-time control", "hard real-time", "zephyr"],
        "Robot sensors (LiDAR, radar, IMU)": ["lidar", "=radar", "=IMU", "=IMUs", "=GNSS", "=GPS",
                                              "inertial measurement", "time-of-flight"],
        "Hardware interfaces": ["can bus", "=CAN", "=I2C", "=SPI", "=UART", "ethercat", "=PCB"],
        "FPGA and hardware design": ["=FPGA", "=FPGAs", "verilog", "vhdl", "systemverilog", "=RTL", "=ASIC"],
        "Mechatronics and actuators": ["mechatronics", "mechatronic", "actuators", "actuator", "motor control",
                                       "electromechanical"],
        "Guidance, navigation and control": ["=GNC", "=GN&C", "guidance, navigation", "guidance and navigation",
                                             "autonomous navigation", "flight software", "flight control"],
        "Safety-critical systems": ["safety-critical", "safety critical", "functional safety", "iso 26262",
                                    "do-178", "safety case", "safety assurance", "mission-critical"],
        "Hardware testing and validation": ["hardware-in-the-loop", "=HIL", "software-in-the-loop", "=SIL",
                                            "verification and validation", "test and validation",
                                            "hardware testing", "system validation", "integration and test"],
        "Electrical engineering": ["electrical engineering", "circuit design", "schematics", "schematic",
                                   "power electronics", "analog circuits", "electronics", "oscilloscope"],
        "Autonomous vehicles": ["autonomous vehicles", "autonomous driving", "self-driving", "autonomous vehicle",
                                "=ADAS", "autonomous systems", "drones", "=UAV", "=UAVs", "unmanned"],
    },
}


# Tools are products, libraries, and languages. Catalog course descriptions name concepts,
# not tools, so a tool's absence from the catalog does NOT show it is untaught. Tools are
# reported as market demand only. Everything else is a concept and gets a curriculum gap score.
TOOL_CATEGORIES = {"Programming languages", "Databases", "Cloud and infrastructure"}
TOOL_SKILLS = {
    "PyTorch", "TensorFlow", "JAX", "scikit-learn", "Hugging Face", "Gradient boosting libraries",
    "GPU programming (CUDA)", "Model serving", "MLOps", "LLM frameworks", "Spark", "Kafka and streaming",
    "Workflow orchestration", "dbt", "Data warehousing", "Databricks and lakehouse", "Hadoop ecosystem",
    "Distributed query engines", "Version control (Git)", "BI tools", "Excel / spreadsheets", "Pandas / NumPy",
    "ROS", "FPGA and hardware design", "Hardware interfaces",
}


# Practices (built through project work, rarely listed as catalog topics) and industry domains
# are also reported as demand only.
DEMAND_ONLY = {"Debugging", "Code review", "Software testing", "Agile practices", "Autonomous vehicles"}

CONCEPT_OVERRIDES = {"Relational databases", "Graph databases", "High-performance computing", "Cloud computing"}


def kind(skill: "Skill") -> str:
    """concept (gets a curriculum gap score), tool, or practice/domain (demand only)."""
    if skill.name in DEMAND_ONLY:
        return "practice"
    return "tool" if is_tool(skill) else "concept"


def is_tool(skill: "Skill") -> bool:
    if skill.name in CONCEPT_OVERRIDES:
        return False
    return skill.category in TOOL_CATEGORIES or skill.name in TOOL_SKILLS


def build() -> list[Skill]:
    return [Skill(name, cat, tuple(aliases)) for cat, skills in _RAW.items() for name, aliases in skills.items()]


SKILLS: list[Skill] = build()
CATEGORIES: list[str] = list(_RAW)


def validate(skills: list[Skill] = SKILLS) -> None:
    """Raise if any surface form belongs to two skills, or a skill has no aliases."""
    owner: dict[str, str] = {}
    names = set()
    for s in skills:
        if s.name in names:
            raise ValueError(f"duplicate skill name: {s.name}")
        names.add(s.name)
        if not s.aliases:
            raise ValueError(f"skill without aliases: {s.name}")
        for a in s.aliases:
            key = a if a.startswith(("=", "re=")) else a.lower()
            if key in owner and owner[key] != s.name:
                raise ValueError(f"alias {a!r} used by both {owner[key]} and {s.name}")
            owner[key] = s.name


validate()
