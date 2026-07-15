## Setup TPC-DI & Generate Sample Data
> You should have Java 8 installed and set in your local environment variables to run the TPC-DI data generator.
1. Download the TPC-DI data generator from the official [TPC website](https://www.tpc.org/tpc_documents_current_versions/download_programs/tools-download-request5.asp?bm_type=TPC-DI&bm_vers=1.1.0&mode=CURRENT-ONLY). 
2. Extract the downloaded ZIP file and run `java -jar DIGen.jar -sf 3 -o ../data` in the terminal. 