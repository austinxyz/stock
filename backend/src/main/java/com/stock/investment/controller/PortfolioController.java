package com.stock.investment.controller;

import com.stock.investment.dto.PortfolioRequest;
import com.stock.investment.dto.PortfolioResponse;
import com.stock.investment.service.PortfolioService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/portfolios")
@RequiredArgsConstructor
public class PortfolioController {

    private final PortfolioService portfolioService;

    @GetMapping
    public ResponseEntity<List<PortfolioResponse>> getUserPortfolios() {
        List<PortfolioResponse> portfolios = portfolioService.getUserPortfolios();
        return ResponseEntity.ok(portfolios);
    }

    @GetMapping("/{id}")
    public ResponseEntity<PortfolioResponse> getPortfolioById(@PathVariable Long id) {
        PortfolioResponse portfolio = portfolioService.getPortfolioById(id);
        return ResponseEntity.ok(portfolio);
    }

    @PostMapping
    public ResponseEntity<PortfolioResponse> createPortfolio(@Valid @RequestBody PortfolioRequest request) {
        PortfolioResponse created = portfolioService.createPortfolio(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<PortfolioResponse> updatePortfolio(
            @PathVariable Long id,
            @Valid @RequestBody PortfolioRequest request) {
        PortfolioResponse updated = portfolioService.updatePortfolio(id, request);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deletePortfolio(@PathVariable Long id) {
        portfolioService.deletePortfolio(id);
        return ResponseEntity.noContent().build();
    }
}
